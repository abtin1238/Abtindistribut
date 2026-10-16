from __future__ import annotations
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.services.importer import ENTITIES, ImportError_, cell_text, coerce_rows, detect, key_norm, load_tables, map_headers
import json
import os
from decimal import Decimal
from sqlalchemy import select
from app.core.common import Q2, audit, next_seq
from app.core.security import has_perm, wh_scope
from app.models import Brand, Category, Customer, Product, Stock, StockMove, Supplier, Warehouse
from app.modules.platform import MAX_UPLOAD
from app.services.accounting import AP, AR, OPEN_EQ, party_balances, post_entry, post_stock_adjust

Q3=Decimal('0.001')

PERMS={'products':['catalog.write'],'stock':['inventory.write'],'customers':['crm.write'],'suppliers':['purchase.write']}

def _s(v): return format(v,'f') if isinstance(v,Decimal) else ('' if v is None else v)

def _req(ctx,perms):
 for p in perms:
  if not has_perm(ctx[2],p): raise HTTPException(403,'دسترسی کافی نیست')

def _wh(s,ctx,warehouse_id):
 cid=ctx[1];sc=wh_scope(s,ctx);whs=[w for w in s.scalars(select(Warehouse).where(Warehouse.company_id==cid,Warehouse.active==True)) if sc is None or w.id in sc]  # noqa: E712
 by={key_norm(w.name):w for w in whs};default=None
 if warehouse_id:
  default=next((w for w in whs if w.id==warehouse_id),None)
  if not default: raise HTTPException(404,'انبار یافت نشد')
 elif len(whs)==1: default=whs[0]
 def res(name):
  if name:
   w=by.get(key_norm(name));return (w,None) if w else (None,f'انبار «{name}» یافت نشد')
  return (default,None) if default else (None,'انبار مشخص نشده؛ انبار پیش‌فرض را انتخاب کنید')
 return res,whs

def _set_stock(s,cid,uid,w,pid,target,ref):
 """موجودی را روی مقدار فایل تنظیم می‌کند (نه جمع شدن با قبلی)؛ تفاضل به‌صورت حرکت in/out ثبت می‌شود."""
 st=s.scalar(select(Stock).where(Stock.warehouse_id==w.id,Stock.product_id==pid).with_for_update())
 if st is None: st=Stock(warehouse_id=w.id,product_id=pid,quantity=Decimal(0),reserved=Decimal(0));s.add(st);s.flush()
 if target<st.reserved: raise ValueError(f'موجودی فایل ({_s(target)}) کمتر از مقدار رزروشده ({_s(st.reserved)}) است')
 d=target-st.quantity
 if d!=0: st.quantity=target;s.add(StockMove(company_id=cid,warehouse_id=w.id,product_id=pid,kind='in' if d>0 else 'out',quantity=abs(d),reference=ref,user_id=uid));post_stock_adjust(s,cid,uid,s.get(Product,pid),d,ref,opening=True)

def _named(s,model,cid):
 return {key_norm(x.name):x for x in s.scalars(select(model).where(model.company_id==cid))}

def _get_or_make(s,model,cid,cache,name):
 if not name: return None
 k=key_norm(name);x=cache.get(k)
 if x is None: x=model(company_id=cid,name=name);s.add(x);s.flush();cache[k]=x
 return x

def _cmp(old,new,num=False):
 if new is None or new=='': return False
 if num: return Decimal(str(old or 0))!=Decimal(str(new))
 return fa(old)!=fa(new)

def fa(x): return cell_text(x)

def _products(s,ctx,rows,apply,wid,has_stock,entity):
 u,cid,_=ctx;res,whs=_wh(s,ctx,wid);ref=f'import:{entity}'
 ex={};[ex.setdefault(key_norm(p.sku),p) for p in s.scalars(select(Product).where(Product.company_id==cid))]
 brands=_named(s,Brand,cid);cats=_named(s,Category,cid)
 stocks={(x.warehouse_id,x.product_id):x for x in s.scalars(select(Stock).join(Warehouse,Warehouse.id==Stock.warehouse_id).where(Warehouse.company_id==cid))} if has_stock else {}
 out=[]
 for r in rows:
  v=r['values'];msgs=list(r['errors']);ch=[];p=ex.get(key_norm(v.get('sku','')));st='new' if p is None else 'unchanged';w=None;target=None
  if p is None and entity=='stock' and not msgs: msgs.append('کالا با این کد یافت نشد؛ ابتدا از نوع «کالا و قیمت» وارد کنید')
  if p is None and entity=='products' and not v.get('name') and not msgs: msgs.append('نام کالا برای کالای جدید لازم است')
  if not msgs and entity=='products':
   if p is not None:
    for f,num in (('name',0),('unit',0),('base_price',1),('min_stock',1)):
     if _cmp(getattr(p,f),v.get(f),num): ch.append({'field':f,'old':_s(getattr(p,f)),'new':_s(v[f])})
    for f,cache,fk in (('brand',brands,'brand_id'),('category',cats,'category_id')):
     if v.get(f):
      o=next((x for x in cache.values() if x.id==getattr(p,fk)),None)
      if not o or key_norm(o.name)!=key_norm(v[f]): ch.append({'field':f,'old':o.name if o else '','new':v[f]})
    if ch: st='update'
  if not msgs and has_stock and v.get('quantity') is not None:
   w,e=res(v.get('warehouse',''))
   if e: msgs.append(e)
   else:
    target=v['quantity'].quantize(Q3);cur=stocks.get((w.id,p.id)) if p else None
    old=cur.quantity if cur else Decimal(0)
    if cur and target<cur.reserved: msgs.append(f'موجودی فایل کمتر از مقدار رزروشده ({_s(cur.reserved)}) است')
    elif target!=old: ch.append({'field':'quantity','old':_s(old),'new':_s(target)});st='update' if st=='unchanged' else st
  if msgs: out.append({'line':r['line'],'status':'error','label':v.get('name') or v.get('sku',''),'messages':msgs,'changes':[],'values':v});continue
  if apply and st in ('new','update'):
   try:
    with s.begin_nested():
     if p is None:
      p=Product(company_id=cid,sku=v['sku'],name=v['name'],unit=v.get('unit') or 'عدد',base_price=(v.get('base_price') or Decimal(0)).quantize(Q2),min_stock=(v.get('min_stock') or Decimal(0)).quantize(Q2),brand_id=getattr(_get_or_make(s,Brand,cid,brands,v.get('brand')),'id',None),category_id=getattr(_get_or_make(s,Category,cid,cats,v.get('category')),'id',None));s.add(p);s.flush();ex[key_norm(p.sku)]=p
     elif entity=='products':
      for c in ch:
       f=c['field']
       if f=='brand': p.brand_id=_get_or_make(s,Brand,cid,brands,v['brand']).id
       elif f=='category': p.category_id=_get_or_make(s,Category,cid,cats,v['category']).id
       elif f in ('base_price',): p.base_price=v[f].quantize(Q2)
       elif f=='min_stock': p.min_stock=v[f].quantize(Q2)
       elif f!='quantity': setattr(p,f,v[f])
     if w is not None and target is not None: _set_stock(s,cid,u.id,w,p.id,target,ref)
   except ValueError as e: out.append({'line':r['line'],'status':'error','label':v.get('name') or v.get('sku',''),'messages':[str(e)],'changes':[],'values':v});continue
  out.append({'line':r['line'],'status':st,'label':v.get('name') or v.get('sku',''),'messages':[],'changes':ch,'values':v})
 return out

def _parties(s,ctx,rows,apply,entity):
 u,cid,_=ctx;cust=entity=='customers';M=Customer if cust else Supplier;kind='customer' if cust else 'supplier';acc=AR if cust else AP
 bal=party_balances(s,cid,kind);ex_code={};ex_name={}
 for x in s.scalars(select(M).where(M.company_id==cid)):
  if cust: ex_code.setdefault(key_norm(x.code),x)
  ex_name.setdefault(key_norm(x.name),x)
 out=[];fields=('name','phone','address','region','customer_group') if cust else ('name','phone')
 for r in rows:
  v=r['values'];msgs=list(r['errors']);ch=[];code=v.get('code','') if cust else ''
  p=ex_code.get(key_norm(code)) if code else None
  if p is None and not code: p=ex_name.get(key_norm(v.get('name','')))
  warn=[]
  if p is None and ex_name.get(key_norm(v.get('name',''))): warn.append('مشتری/تأمین‌کننده‌ای با همین نام وجود دارد؛ رکورد جدید ساخته می‌شود')
  st='new' if p is None else 'unchanged'
  if not msgs and p is not None:
   for f in fields:
    if _cmp(getattr(p,f,''),v.get(f)): ch.append({'field':f,'old':_s(getattr(p,f,'')),'new':_s(v[f])})
   if cust and v.get('credit_limit') is not None and _cmp(p.credit_limit,v['credit_limit'],True): ch.append({'field':'credit_limit','old':_s(p.credit_limit),'new':_s(v['credit_limit'])})
  tgt=v.get('_balance');diff=Decimal(0)
  if not msgs and tgt is not None:
   tgt=tgt.quantize(Q2);cur=bal.get(p.id,Decimal(0)) if p else Decimal(0);diff=tgt-cur
   if diff!=0: ch.append({'field':'balance','old':_s(cur),'new':_s(tgt)})
  if ch and st=='unchanged': st='update'
  if msgs: out.append({'line':r['line'],'status':'error','label':v.get('name',''),'messages':msgs,'changes':[],'values':v});continue
  if apply and st in ('new','update'):
   try:
    with s.begin_nested():
     if p is None:
      p=Customer(company_id=cid,code=code or f'IMP-{next_seq(s,f"impcust{cid}"):05d}',name=v['name'],phone=v.get('phone',''),address=v.get('address',''),region=v.get('region',''),customer_group=v.get('customer_group',''),credit_limit=(v.get('credit_limit') or Decimal(0)).quantize(Q2)) if cust else Supplier(company_id=cid,name=v['name'],phone=v.get('phone',''))
      s.add(p);s.flush();ex_name.setdefault(key_norm(p.name),p)
      if cust: ex_code.setdefault(key_norm(p.code),p)
     else:
      for c in ch:
       if c['field']=='credit_limit': p.credit_limit=v['credit_limit'].quantize(Q2)
       elif c['field']!='balance': setattr(p,c['field'],v[c['field']])
     if diff!=0:
      a=abs(diff);dr_acc=(diff>0)==cust  # مشتری: افزایش مانده=بدهکار AR؛ تأمین‌کننده: افزایش مانده=بستانکار AP
      lines=[{'code':acc,'debit' if dr_acc else 'credit':a,('customer_id' if cust else 'supplier_id'):p.id},{'code':OPEN_EQ,'credit' if dr_acc else 'debit':a}]
      post_entry(s,cid,u.id,f'تعدیل مانده از ورود اطلاعات — {p.name}',lines,source=('import_balance',p.id))
   except (ValueError,HTTPException) as e: out.append({'line':r['line'],'status':'error','label':v.get('name',''),'messages':[str(getattr(e,'detail',e))],'changes':[],'values':v});continue
  out.append({'line':r['line'],'status':st,'label':v.get('name',''),'messages':warn,'changes':ch,'values':v})
 return out

def _run(s,ctx,file,entity,mapping,sheet,header_row,warehouse_id,apply,strict):
 data=file.file.read(MAX_UPLOAD+1)
 if len(data)>MAX_UPLOAD: raise HTTPException(413,'حجم فایل بیش از حد مجاز است')
 fname=os.path.basename(file.filename or 'file')[:200]
 try: tables=load_tables(data,fname)
 except ImportError_ as e: raise HTTPException(400,str(e)) from e
 names=list(tables)
 if sheet and sheet not in tables: raise HTTPException(400,'برگه‌ی انتخابی یافت نشد')
 if not sheet: sheet=max(names,key=lambda n:detect(tables[n])[2])
 rows=tables[sheet];hr,det,_=detect(rows)
 if header_row: hr=max(0,min(header_row-1,len(rows)-1))
 entity=entity or det
 if entity and entity not in ENTITIES: raise HTTPException(400,'نوع داده نامعتبر است')
 if hr>=len(rows): raise HTTPException(400,'ردیف سرستون نامعتبر است')
 heads=[cell_text(c) for c in rows[hr]];ncol=max([len(r) for r in rows[hr:hr+200]]+[len(heads)]);heads+=['']*(ncol-len(heads))
 base={'file':fname,'sheet':sheet,'sheets':names,'header_row':hr+1,'detected_entity':det,'entity':entity,'entities':{k:v['label'] for k,v in ENTITIES.items()},'applied':False,'sample':[[cell_text(c) for c in r][:ncol] for r in rows[hr:hr+6]]}
 if not entity:
  base['columns']=[{'index':i,'header':h,'field':''} for i,h in enumerate(heads)];base['fields']=[];base['summary']=None;base['rows']=[];base['issues']=['نوع داده‌ی فایل تشخیص داده نشد؛ نوع را دستی انتخاب کنید.'];return base
 spec=ENTITIES[entity];_req(ctx,PERMS[entity])
 auto={i:f for i,(f,_) in map_headers(entity,heads).items()}
 if mapping:
  try: mp={int(k):v for k,v in json.loads(mapping).items() if v}
  except (ValueError,AttributeError) as e: raise HTTPException(400,'نگاشت ستون‌ها نامعتبر است') from e
  if any(v not in spec['fields'] for v in mp.values()) or len(set(mp.values()))!=len(mp) or any(k<0 or k>=ncol for k in mp): raise HTTPException(400,'نگاشت ستون‌ها نامعتبر است (فیلد ناشناخته یا تکراری)')
 else: mp=auto
 mapped={f for f in mp.values()};issues=[]
 for f,(lab,rq,_) in spec['fields'].items():
  if rq and f not in mapped: issues.append(f'ستون «{lab}» نگاشت نشده است')
 if entity in ('customers','suppliers') and mapped&{'balance','debit','credit'}: _req(ctx,['finance.write'])
 if entity=='products' and 'quantity' in mapped: _req(ctx,['inventory.write'])
 coerced=coerce_rows(entity,rows,hr,mp);live=[r for r in coerced if not r['skip']]
 if len(live)>20000: raise HTTPException(400,'تعداد سطرها بیش از حد مجاز است')
 blocked=bool(issues)
 if blocked: res=[{'line':r['line'],'status':'error','label':r['values'].get('name') or r['values'].get('sku',''),'messages':issues,'changes':[],'values':r['values']} for r in live]
 elif entity in ('products','stock'): res=_products(s,ctx,live,apply,warehouse_id,'quantity' in mapped,entity)
 else: res=_parties(s,ctx,live,apply,entity)
 cnt={k:sum(1 for x in res if x['status']==k) for k in ('new','update','unchanged','error')};cnt['total']=len(res);cnt['skipped']=len(coerced)-len(live)
 if apply:
  if blocked or (strict and cnt['error']): s.rollback();raise HTTPException(409,'ثبت انجام نشد: '+('نگاشت ناقص است' if blocked else f'{cnt["error"]} ردیف خطا دارد (حالت سخت‌گیرانه)'))
  audit(s,ctx[1],ctx[0].id,'import',entity,None,{'file':fname,'sheet':sheet,**cnt});s.commit();base['applied']=True
 else: s.rollback()
 for r in res: r['values']={k:_s(x) for k,x in r['values'].items() if not k.startswith('_')}
 base.update({'columns':[{'index':i,'header':h,'field':mp.get(i,''),'auto':auto.get(i,'')==mp.get(i,'')} for i,h in enumerate(heads)],'fields':[{'key':k,'label':v[0],'required':v[1]} for k,v in spec['fields'].items()],'summary':cnt,'rows':res[:300],'errors':[x for x in res if x['status']=='error'][:500],'issues':issues})
 return base

def import_entities(ctx):
 return {k: {'label': v['label'], 'fields': [{'key': f, 'label': d[0], 'required': d[1]} for f, d in v['fields'].items()]} for k, v in ENTITIES.items()}

def import_preview(file: UploadFile, entity: str, mapping: str, sheet: str, header_row: Optional[int], warehouse_id: Optional[int], ctx, s: Session):
 return _run(s,ctx,file,entity,mapping,sheet,header_row,warehouse_id,False,False)

def import_commit(file: UploadFile, entity: str, mapping: str, sheet: str, header_row: Optional[int], warehouse_id: Optional[int], strict: bool, ctx, s: Session):
 return _run(s,ctx,file,entity,mapping,sheet,header_row,warehouse_id,True,strict)
