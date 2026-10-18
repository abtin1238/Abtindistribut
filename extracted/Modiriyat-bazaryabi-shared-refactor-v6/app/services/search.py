"""جستجوی سراسری و فیلتر پیشرفته روی مشتری/کالا/سفارش/فاکتور/سند حسابداری.

- فیلتر فقط از فهرست سفید (فیلد×عملگر) ساخته می‌شود؛ هیچ نام ستون/عبارت خام از کاربر به SQL نمی‌رسد.
- متن: هر کلمه باید در یکی از ستون‌های متنی باشد (ILIKE با escape؛ در PostgreSQL با ایندکس pg_trgm سریع می‌شود).
- Data Scope: سفارش/فاکتور بدون `data.all` فقط مربوط به خود کاربر؛ هر موجودیت مجوز خودش را می‌خواهد.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from sqlalchemy import and_,case,func,or_,select
from app.core.common import ESC,like_pat
from app.core.security import branch_clause,has_all,has_perm,own_orders
from app.models import Customer,Invoice,JournalEntry,Order,Product
from app.services.jalali import parse_jalali

OPS={'str':('eq','ne','contains','startswith','in'),'num':('eq','ne','gt','gte','lt','lte'),'date':('eq','gte','lte'),'bool':('eq',),'int':('eq','in')}
MAX_FILTERS=10;MAX_TOKENS=5;MAX_PAGE=100
def col(key,label,kind='text'): return {'key':key,'label':label,'kind':kind}
def _customers(cid,u,r):
 q=select(Customer).where(Customer.company_id==cid);c=branch_clause(Customer.branch_id,u,cid,r)
 return q if c is None else q.where(c)
def _products(cid,u,r): return select(Product).where(Product.company_id==cid)
def _orders(cid,u,r):
 q=select(Order,Customer.name.label('customer_name')).join(Customer,Customer.id==Order.customer_id).where(Order.company_id==cid)
 return q if has_all(r) else q.where(own_orders(u))
def _invoices(cid,u,r):
 q=select(Invoice,Order.number.label('order_number'),Customer.name.label('customer_name')).join(Order,Order.id==Invoice.order_id).join(Customer,Customer.id==Order.customer_id).where(Invoice.company_id==cid)
 return q if has_all(r) else q.where(own_orders(u))
def _journal(cid,u,r): return select(JournalEntry).where(JournalEntry.company_id==cid)
def _rowify(spec,entity,x):
 t=tuple(x)
 return spec['row'](t if entity in ('orders','invoices') else t[0])
SPEC={
 'customers':{'label':'مشتریان','perm':'crm.read','page':'customers','q':_customers,'text':[Customer.name,Customer.code,Customer.phone,Customer.region],'fields':{'name':(Customer.name,'str'),'code':(Customer.code,'str'),'phone':(Customer.phone,'str'),'region':(Customer.region,'str'),'group':(Customer.customer_group,'str'),'active':(Customer.active,'bool'),'credit_limit':(Customer.credit_limit,'num'),'id':(Customer.id,'int')},'sort':{'name':Customer.name,'code':Customer.code,'credit_limit':Customer.credit_limit,'id':Customer.id},'default_sort':'name',
  'cols':[col('code','کد'),col('name','نام'),col('region','منطقه'),col('phone','تلفن'),col('credit_limit','سقف اعتبار','money'),col('active','فعال','bool')],'row':lambda x:{'id':x.id,'code':x.code,'name':x.name,'region':x.region,'phone':x.phone,'credit_limit':x.credit_limit,'active':x.active},'title':lambda d:d['name'],'sub':lambda d:f"{d['code']} — {d['region'] or ''}"},
 'products':{'label':'کالاها','perm':'catalog.read','page':'products','q':_products,'text':[Product.name,Product.sku],'fields':{'name':(Product.name,'str'),'sku':(Product.sku,'str'),'unit':(Product.unit,'str'),'brand_id':(Product.brand_id,'int'),'category_id':(Product.category_id,'int'),'base_price':(Product.base_price,'num'),'min_stock':(Product.min_stock,'num'),'active':(Product.active,'bool'),'id':(Product.id,'int')},'sort':{'name':Product.name,'sku':Product.sku,'base_price':Product.base_price,'id':Product.id},'default_sort':'name',
  'cols':[col('sku','کد کالا'),col('name','نام'),col('unit','واحد'),col('base_price','قیمت پایه','money'),col('min_stock','حداقل موجودی','qty'),col('active','فعال','bool')],'row':lambda x:{'id':x.id,'sku':x.sku,'name':x.name,'unit':x.unit,'base_price':x.base_price,'min_stock':x.min_stock,'active':x.active},'title':lambda d:d['name'],'sub':lambda d:d['sku']},
 'orders':{'label':'سفارش‌ها','perm':'sales.read','page':'orders','q':_orders,'text':[Order.number,Customer.name],'fields':{'number':(Order.number,'str'),'status':(Order.status,'str'),'customer':(Customer.name,'str'),'customer_id':(Order.customer_id,'int'),'seller_id':(Order.seller_id,'int'),'warehouse_id':(Order.warehouse_id,'int'),'total':(Order.total,'num'),'created_at':(Order.created_at,'date'),'id':(Order.id,'int')},'sort':{'created_at':Order.created_at,'total':Order.total,'number':Order.number,'id':Order.id},'default_sort':'id',
  'cols':[col('number','شماره'),col('created_at','تاریخ','date'),col('customer','مشتری'),col('status','وضعیت'),col('total','مبلغ','money')],'row':lambda x:{'id':x[0].id,'number':x[0].number,'created_at':x[0].created_at,'customer':x[1],'status':x[0].status,'total':x[0].total},'title':lambda d:d['number'],'sub':lambda d:f"{d['customer']} — {d['status']}"},
 'invoices':{'label':'فاکتورها','perm':'sales.read','page':'invoices','q':_invoices,'text':[Invoice.number,Customer.name,Order.number],'fields':{'number':(Invoice.number,'str'),'status':(Invoice.status,'str'),'customer':(Customer.name,'str'),'customer_id':(Order.customer_id,'int'),'total':(Invoice.total,'num'),'paid':(Invoice.paid,'num'),'issued_at':(Invoice.issued_at,'date'),'id':(Invoice.id,'int')},'sort':{'issued_at':Invoice.issued_at,'total':Invoice.total,'number':Invoice.number,'id':Invoice.id},'default_sort':'id',
  'cols':[col('number','شماره'),col('issued_at','تاریخ','date'),col('customer','مشتری'),col('status','وضعیت'),col('total','جمع کل','money'),col('paid','پرداخت‌شده','money')],'row':lambda x:{'id':x[0].id,'number':x[0].number,'issued_at':x[0].issued_at,'customer':x[2],'status':x[0].status,'total':x[0].total,'paid':x[0].paid},'title':lambda d:d['number'],'sub':lambda d:f"{d['customer']} — {d['status']}"},
 'journal':{'label':'اسناد حسابداری','perm':'finance.read','page':'accounting','q':_journal,'text':[JournalEntry.number,JournalEntry.description],'fields':{'number':(JournalEntry.number,'str'),'description':(JournalEntry.description,'str'),'status':(JournalEntry.status,'str'),'source_type':(JournalEntry.source_type,'str'),'debit':(JournalEntry.debit,'num'),'created_at':(JournalEntry.created_at,'date'),'id':(JournalEntry.id,'int')},'sort':{'created_at':JournalEntry.created_at,'debit':JournalEntry.debit,'number':JournalEntry.number,'id':JournalEntry.id},'default_sort':'id',
  'cols':[col('number','شماره سند'),col('created_at','تاریخ','date'),col('description','شرح'),col('debit','مبلغ','money'),col('status','وضعیت')],'row':lambda x:{'id':x.id,'number':x.number,'created_at':x.created_at,'description':x.description,'debit':x.debit,'status':x.status},'title':lambda d:d['number'],'sub':lambda d:d['description']},
}
def allowed(r): return {k:v for k,v in SPEC.items() if has_perm(r,v['perm'])}
def schema(r): return {k:{'label':v['label'],'page':v['page'],'fields':[{'name':n,'type':t,'ops':list(OPS[t])} for n,(c,t) in v['fields'].items()],'sort':list(v['sort']),'columns':v['cols']} for k,v in allowed(r).items()}
def _spec(entity,r):
 if entity not in SPEC: raise HTTPException(400,'نوع جستجو نامعتبر است: '+str(entity))
 if not has_perm(r,SPEC[entity]['perm']): raise HTTPException(403,'دسترسی کافی نیست')
 return SPEC[entity]
def _val(kind,v,field):
 try:
  if kind=='num': return Decimal(str(v))
  if kind=='int': return int(v)
  if kind=='bool':
   if isinstance(v,bool): return v
   if str(v).lower() in ('1','true','yes'): return True
   if str(v).lower() in ('0','false','no'): return False
   raise ValueError
  if kind=='date':
   d=parse_jalali(v) if '/' in str(v) else date.fromisoformat(str(v)[:10]);return d
  s=str(v)
  if len(s)>200: raise ValueError
  return s
 except (ValueError,InvalidOperation,TypeError): raise HTTPException(400,f'مقدار فیلتر «{field}» نامعتبر است')
def _cond(spec,f):
 if not isinstance(f,dict): raise HTTPException(400,'فیلتر نامعتبر است')
 name,op,v=f.get('field'),f.get('op','eq'),f.get('value')
 if name not in spec['fields']: raise HTTPException(400,f'فیلد «{name}» مجاز نیست')
 c,kind=spec['fields'][name]
 if op not in OPS[kind]: raise HTTPException(400,f'عملگر «{op}» برای فیلد «{name}» مجاز نیست')
 if op=='in':
  if not isinstance(v,list) or not v or len(v)>50: raise HTTPException(400,'مقدار in باید فهرست ۱ تا ۵۰ موردی باشد')
  return c.in_([_val(kind if kind!='str' else 'str',x,name) for x in v])
 if kind=='date':
  d=_val('date',v,name);a=datetime.combine(d,datetime.min.time());b=a+timedelta(days=1)
  return {'eq':and_(c>=a,c<b),'gte':c>=a,'lte':c<b}[op]
 x=_val(kind,v,name)
 if kind=='str':
  if op=='contains': return c.ilike(like_pat(x),escape=ESC)
  if op=='startswith': return c.ilike(like_pat(x)[1:],escape=ESC)
  return (func.lower(c)==x.lower()) if op=='eq' else (func.lower(c)!=x.lower())
 return {'eq':c==x,'ne':c!=x,'gt':c>x,'gte':c>=x,'lt':c<x,'lte':c<=x}[op]
def _text(spec,q):
 toks=[t for t in str(q or '').split() if t][:MAX_TOKENS];cs=[]
 for t in toks:
  if len(t)>100: raise HTTPException(400,'متن جستجو بیش از حد طولانی است')
  cs.append(or_(*[c.ilike(like_pat(t),escape=ESC) for c in spec['text']]))
 return cs
def validate_query(r,entity,query):
 """اعتبارسنجی یک پرسمان ذخیره‌شده/ورودی بدون اجرا"""
 spec=_spec(entity,r);qq=query or {}
 fl=qq.get('filters') or []
 if not isinstance(fl,list) or len(fl)>MAX_FILTERS: raise HTTPException(400,f'حداکثر {MAX_FILTERS} فیلتر مجاز است')
 for f in fl: _cond(spec,f)
 if qq.get('sort') and qq['sort'] not in spec['sort']: raise HTTPException(400,'مبنای مرتب‌سازی مجاز نیست')
 if qq.get('order') not in (None,'asc','desc'): raise HTTPException(400,'جهت مرتب‌سازی نامعتبر است')
 return {'q':str(qq.get('q') or '')[:200],'filters':fl,'sort':qq.get('sort') or None,'order':qq.get('order') or None}
def advanced(s,ctx,entity,query,page=1,page_size=25):
 u,cid,r=ctx;spec=_spec(entity,r);qq=validate_query(r,entity,query);page=max(1,int(page));page_size=min(MAX_PAGE,max(1,int(page_size)))
 q=spec['q'](cid,u,r)
 for c in _text(spec,qq['q'])+[_cond(spec,f) for f in qq['filters']]: q=q.where(c)
 total=s.scalar(select(func.count()).select_from(q.order_by(None).subquery())) or 0
 sc=spec['sort'][qq['sort'] or spec['default_sort']];desc_=(qq['order'] or ('desc' if (qq['sort'] or spec['default_sort']) in ('id','created_at','issued_at') else 'asc'))=='desc'
 q=q.order_by(sc.desc() if desc_ else sc.asc(),spec['sort']['id'].desc()).limit(page_size).offset((page-1)*page_size)
 rows=[_rowify(spec,entity,x) for x in s.execute(q)]
 return {'entity':entity,'columns':spec['cols'],'rows':rows,'total':total,'page':page,'page_size':page_size,'query':qq}
def global_search(s,ctx,text,types=None,limit=5):
 """جستجوی سراسری: برای هر موجودیتِ مجاز بهترین نتایج (اولویت با شروع‌شدن عنوان با متن)"""
 u,cid,r=ctx;limit=min(20,max(1,int(limit)));out={}
 for k,spec in allowed(r).items():
  if types and k not in types: continue
  q=spec['q'](cid,u,r)
  for c in _text(spec,text): q=q.where(c)
  first=spec['text'][0];pri=case((first.ilike(like_pat(text.strip())[1:],escape=ESC),0),else_=1)
  rows=[]
  for x in s.execute(q.order_by(pri,spec['sort'][spec['default_sort']].asc() if spec['default_sort']=='name' else spec['sort']['id'].desc()).limit(limit)):
   d=_rowify(spec,k,x);rows.append({'id':d['id'],'title':spec['title'](d),'sub':spec['sub'](d)})
  out[k]={'label':spec['label'],'page':spec['page'],'items':rows}
 return out
