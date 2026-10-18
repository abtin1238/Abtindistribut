"""گزارش‌های مدیریتی (فروش، مشتری، انبار، بازاریاب، مأمور پخش، مالی).

همهٔ محاسبات اینجا و از دیتابیس است؛ فرانت فقط نمایش می‌دهد.
هر گزارش یک «جدول» استاندارد برمی‌گرداند تا JSON، Excel و PDF از یک منبع ساخته شوند:
    {'title','columns':[{'key','label','kind'}],'rows':[dict],'summary':[[label,value,kind]],'filters':{}}
kind یکی از: text | int | qty | money | pct | date | datetime
دسترسی داده (Data Scope): بدون `data.all` فقط داده‌ی خود کاربر دیده می‌شود.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,timedelta
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func,select
from app.core.common import D,Q2
from app.core.security import has_all,has_perm,wh_scope
from app.models import Account,Branch,Category,Check,Customer,Delivery,JournalEntry,JournalLine,Lead,Order,OrderItem,Product,Stock,StockMove,Target,User,Visit,Warehouse
from app.services.accounting import AP,AR,BANK,CASH,COGS,INVT,NP,NR,VAT,bank_codes,party_balances
from app.services.jalali import parse_jalali

def col(key,label,kind='text'): return {'key':key,'label':label,'kind':kind}
def _pct(a,b): return (D(a)*100/D(b)).quantize(Q2) if b else Decimal(0)
def _month_key(d:date): return f'{d.year:04d}-{d.month:02d}'

@dataclass
class Flt:
 start:Optional[date]=None
 end:Optional[date]=None
 user_id:Optional[int]=None
 branch_id:Optional[int]=None
 region:Optional[str]=None
 warehouse_id:Optional[int]=None
 days:int=60
 def dump(self): return {k:(v.isoformat() if isinstance(v,date) else v) for k,v in self.__dict__.items() if v not in (None,'')}

def _date(params,k,jk):
 v=params.get(jk)
 if v not in (None,''):
  try: return parse_jalali(v)
  except ValueError as e: raise HTTPException(400,f'{jk}: {e}')
 v=params.get(k)
 if v in (None,''): return None
 if isinstance(v,date): return v
 try: return date.fromisoformat(str(v))
 except ValueError: raise HTTPException(400,f'{k}: تاریخ نامعتبر است (YYYY-MM-DD)')
def _int(params,k):
 v=params.get(k)
 if v in (None,''): return None
 try: return int(v)
 except (TypeError,ValueError): raise HTTPException(400,f'{k} نامعتبر است')
def make_filter(ctx,params:dict)->Flt:
 """فیلتر استاندارد از پارامترها؛ تاریخ شمسی با jstart/jend، میلادی با start/end. بدون data.all، کاربر فقط خودش را می‌بیند."""
 u,cid,r=ctx;f=Flt(start=_date(params,'start','jstart'),end=_date(params,'end','jend'),user_id=_int(params,'user_id'),branch_id=_int(params,'branch_id'),warehouse_id=_int(params,'warehouse_id'),region=(params.get('region') or None))
 if f.start and f.end and f.start>f.end: raise HTTPException(400,'بازه‌ی تاریخ نامعتبر است')
 d=_int(params,'days')
 if d is not None:
  if not 1<=d<=3650: raise HTTPException(400,'days باید بین ۱ تا ۳۶۵۰ باشد')
  f.days=d
 if not has_all(r): f.user_id=u.id
 return f
def _bounds(q,c,f:Flt):
 if f.start: q=q.where(func.date(c)>=f.start)
 if f.end: q=q.where(func.date(c)<=f.end)
 return q
def _table(title,columns,rows,summary=None,f=None): return {'title':title,'columns':columns,'rows':rows,'summary':summary or [],'filters':f.dump() if f else {}}

# ---------------------------------------------------------------- فروش
SALES_BY={'product':'کالا','customer':'مشتری','seller':'فروشنده','region':'منطقه','branch':'شعبه','day':'روز','category':'دسته‌بندی'}
def _sales_cols():
 return {'product':(Product.id,Product.name),'customer':(Customer.id,Customer.name),'seller':(User.id,User.name),'region':(Customer.region,Customer.region),'branch':(Branch.id,Branch.name),'day':(func.date(Order.created_at),func.date(Order.created_at)),'category':(Category.id,Category.name)}
def _sales_base(q,cid,f:Flt):
 q=q.select_from(OrderItem).join(Order,Order.id==OrderItem.order_id).join(Product,Product.id==OrderItem.product_id).join(Customer,Customer.id==Order.customer_id).join(User,User.id==Order.seller_id).outerjoin(Warehouse,Warehouse.id==Order.warehouse_id).outerjoin(Branch,Branch.id==Warehouse.branch_id).outerjoin(Category,Category.id==Product.category_id).where(Order.company_id==cid,Order.status!='cancelled')
 q=_bounds(q,Order.created_at,f)
 if f.user_id: q=q.where(Order.seller_id==f.user_id)
 if f.branch_id: q=q.where(Warehouse.branch_id==f.branch_id)
 if f.region: q=q.where(Customer.region==f.region)
 return q
def sales_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params);by=params.get('by') or 'product'
 if by not in SALES_BY: raise HTTPException(400,'مبنای گزارش نامعتبر است ('+'/'.join(SALES_BY)+')')
 k,n=_sales_cols()[by];gross=func.sum(OrderItem.quantity*OrderItem.unit_price);disc=func.sum(OrderItem.discount)
 q=_sales_base(select(k,n,func.count(func.distinct(Order.id)),func.sum(OrderItem.quantity),gross,disc),cid,f).group_by(k,n)
 rows=[]
 for key,name,orders,qty,g,dc in s.execute(q):
  g=D(g);dc=D(dc);rows.append({'_key':'' if key is None else str(key),'name':str(name) if name not in (None,'') else '—','orders':orders,'quantity':D(qty),'gross':g,'discount':dc,'net':g-dc})
 tot=sum((x['net'] for x in rows),Decimal(0))
 rows.sort(key=lambda x:x['_key'] if by=='day' else -x['net'])
 for x in rows: x['share']=_pct(x['net'],tot)
 n_orders=s.scalar(_sales_base(select(func.count(func.distinct(Order.id))),cid,f)) or 0
 gs=sum((x['gross'] for x in rows),Decimal(0));ds=sum((x['discount'] for x in rows),Decimal(0))
 cols=[col('name',SALES_BY[by],'date' if by=='day' else 'text'),col('orders','تعداد سفارش','int'),col('quantity','تعداد کالا','qty'),col('gross','فروش ناخالص','money'),col('discount','تخفیف','money'),col('net','فروش خالص','money'),col('share','سهم ٪','pct')]
 if by=='day':
  for x in rows: x['name']=x['_key']
 return _table('گزارش فروش بر اساس '+SALES_BY[by],cols,rows,[['تعداد سفارش',n_orders,'int'],['فروش ناخالص',gs,'money'],['تخفیف',ds,'money'],['فروش خالص',gs-ds,'money'],['میانگین هر سفارش',(gs-ds)/n_orders if n_orders else Decimal(0),'money']],f)
def sales_detail(s,ctx,params):
 """Drill-down: سفارش‌های پشت یک ردیف گزارش فروش"""
 cid=ctx[1];f=make_filter(ctx,params);by=params.get('by') or 'product';key=params.get('key')
 if by not in SALES_BY: raise HTTPException(400,'مبنای گزارش نامعتبر است')
 k,_=_sales_cols()[by];q=_sales_base(select(Order.id,Order.number,Order.status,Order.created_at,Customer.name,User.name,func.sum(OrderItem.quantity*OrderItem.unit_price-OrderItem.discount)),cid,f)
 if by=='region': q=q.where(k==(key or ''))
 elif by=='day':
  try: q=q.where(k==date.fromisoformat(key or ''))
  except ValueError: raise HTTPException(400,'key نامعتبر است')
 elif key in (None,'','null'): q=q.where(k.is_(None))
 else:
  try: q=q.where(k==int(key))
  except ValueError: raise HTTPException(400,'key نامعتبر است')
 q=q.group_by(Order.id,Order.number,Order.status,Order.created_at,Customer.name,User.name).order_by(Order.id.desc()).limit(1000)
 rows=[{'_key':str(i),'number':nm,'status':st,'created_at':at,'customer':c,'seller':sl,'net':D(t)} for i,nm,st,at,c,sl,t in s.execute(q)]
 return _table('سفارش‌های ردیف انتخاب‌شده',[col('number','سفارش'),col('created_at','تاریخ','date'),col('customer','مشتری'),col('seller','فروشنده'),col('status','وضعیت'),col('net','مبلغ (بخش مربوط)','money')],rows,[['جمع',sum((x['net'] for x in rows),Decimal(0)),'money']],f)

# ---------------------------------------------------------------- مشتری
def customers_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params)
 oq=_bounds(select(Order.customer_id,func.count(),func.sum(Order.total)).where(Order.company_id==cid,Order.status!='cancelled'),Order.created_at,f)
 if f.user_id: oq=oq.where(Order.seller_id==f.user_id)
 per={c:(n,D(t)) for c,n,t in s.execute(oq.group_by(Order.customer_id))}
 last={c:d for c,d in s.execute(select(Order.customer_id,func.max(Order.created_at)).where(Order.company_id==cid,Order.status!='cancelled').group_by(Order.customer_id))}
 led=party_balances(s,cid,'customer');cq=select(Customer).where(Customer.company_id==cid)
 if f.region: cq=cq.where(Customer.region==f.region)
 today=date.today();rows=[]
 for c in s.scalars(cq.order_by(Customer.name)):
  n,t=per.get(c.id,(0,Decimal(0)))
  if f.user_id and c.id not in per: continue   # فروشنده‌ی فیلترشده فقط مشتریان خودش را می‌بیند
  lo=last.get(c.id);idle=(today-lo.date()).days if lo else None;bal=led.get(c.id,Decimal(0));lim=D(c.credit_limit)
  rows.append({'_key':str(c.id),'code':c.code,'name':c.name,'region':c.region or '—','orders':n,'sales':t,'last_order':lo,'idle_days':idle,'balance':bal,'credit_limit':lim,'credit_used':_pct(bal,lim) if lim>0 else None,'status':'مسدود' if not c.active else 'راکد' if (idle is None or idle>f.days) else 'فعال'})
 rows.sort(key=lambda x:-x['sales'])
 cols=[col('code','کد'),col('name','مشتری'),col('region','منطقه'),col('orders','سفارش','int'),col('sales','فروش دوره','money'),col('last_order','آخرین سفارش','date'),col('idle_days','روز از آخرین خرید','int'),col('balance','مانده حساب (دفتر)','money'),col('credit_limit','سقف اعتبار','money'),col('credit_used','مصرف اعتبار ٪','pct'),col('status','وضعیت')]
 return _table('گزارش مشتریان',cols,rows,[['تعداد مشتری',len(rows),'int'],['فروش دوره',sum((x['sales'] for x in rows),Decimal(0)),'money'],['مجموع مانده مشتریان',sum((x['balance'] for x in rows),Decimal(0)),'money'],[f'مشتریان راکد (بیش از {f.days} روز)',sum(1 for x in rows if x['status']=='راکد'),'int']],f)

# ---------------------------------------------------------------- انبار
INV_KINDS={'stock':'موجودی و ارزش','low':'کم‌موجودی','dead':'کالای راکد','movement':'گردش کالا'}
IN_KINDS={'in','purchase_in','return_in','transfer_in','transfer_cancel'};OUT_KINDS={'out','transfer_out'}
def inventory_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params);kind=params.get('kind') or 'stock'
 if kind not in INV_KINDS: raise HTTPException(400,'نوع گزارش انبار نامعتبر است ('+'/'.join(INV_KINDS)+')')
 sc=wh_scope(s,ctx)
 if f.warehouse_id and sc is not None and f.warehouse_id not in sc: raise HTTPException(404,'انبار یافت نشد')
 def wq(q,c):
  if sc is not None: q=q.where(c.in_(list(sc)))
  if f.warehouse_id: q=q.where(c==f.warehouse_id)
  return q
 if kind=='movement':
  q=_bounds(wq(select(StockMove.product_id,StockMove.kind,func.sum(StockMove.quantity),func.count()).where(StockMove.company_id==cid),StockMove.warehouse_id),StockMove.created_at,f)
  if f.branch_id: q=q.where(StockMove.warehouse_id.in_(select(Warehouse.id).where(Warehouse.branch_id==f.branch_id)))
  agg={}
  for pid,k,qty,n in s.execute(q.group_by(StockMove.product_id,StockMove.kind)):
   a=agg.setdefault(pid,{'in':Decimal(0),'out':Decimal(0),'moves':0,'kinds':{}});qty=D(qty);a['moves']+=n;a['kinds'][k]=qty
   if k in IN_KINDS: a['in']+=qty
   elif k in OUT_KINDS: a['out']+=qty
  prods={p.id:p for p in s.scalars(select(Product).where(Product.company_id==cid))}
  rows=[{'_key':str(pid),'sku':prods[pid].sku if pid in prods else '','name':prods[pid].name if pid in prods else str(pid),'in_qty':a['in'],'out_qty':a['out'],'net':a['in']-a['out'],'moves':a['moves'],'by_kind':{k:str(v) for k,v in a['kinds'].items()}} for pid,a in agg.items() if pid in prods]
  rows.sort(key=lambda x:-x['out_qty'])
  return _table('گردش کالا',[col('sku','کد کالا'),col('name','کالا'),col('in_qty','ورودی','qty'),col('out_qty','خروجی','qty'),col('net','خالص','qty'),col('moves','تعداد حرکت','int')],rows,[['جمع ورودی',sum((x['in_qty'] for x in rows),Decimal(0)),'qty'],['جمع خروجی',sum((x['out_qty'] for x in rows),Decimal(0)),'qty']],f)
 q=wq(select(Stock,Product,Warehouse).join(Product,Product.id==Stock.product_id).join(Warehouse,Warehouse.id==Stock.warehouse_id).where(Product.company_id==cid,Warehouse.company_id==cid),Stock.warehouse_id)
 if f.branch_id: q=q.where(Warehouse.branch_id==f.branch_id)
 cutoff=datetime.combine(date.today()-timedelta(days=f.days),datetime.min.time())
 out_recent={(w,p) for w,p in s.execute(select(StockMove.warehouse_id,StockMove.product_id).where(StockMove.company_id==cid,StockMove.kind=='out',StockMove.created_at>=cutoff).distinct())}
 last_out={(w,p):d for w,p,d in s.execute(select(StockMove.warehouse_id,StockMove.product_id,func.max(StockMove.created_at)).where(StockMove.company_id==cid,StockMove.kind=='out').group_by(StockMove.warehouse_id,StockMove.product_id))}
 rows=[]
 for st,p,w in s.execute(q.order_by(Product.name,Warehouse.name)):
  qty=D(st.quantity);res=D(st.reserved);avail=qty-res;mn=D(p.min_stock);cost=D(p.avg_cost)
  row={'_key':str(p.id),'sku':p.sku,'name':p.name,'warehouse':w.name,'quantity':qty,'reserved':res,'available':avail,'unit_cost':cost,'value':qty*cost,'min_stock':mn,'shortage':max(Decimal(0),mn-avail),'last_out':last_out.get((w.id,p.id))}
  if kind=='stock' and (qty!=0 or res!=0): rows.append(row)
  elif kind=='low' and (avail<=0 or (mn>0 and avail<=mn)): rows.append(row)
  elif kind=='dead' and qty>0 and (w.id,p.id) not in out_recent: rows.append(row)
 if kind=='low': rows.sort(key=lambda x:-x['shortage'])
 elif kind=='dead': rows.sort(key=lambda x:-x['value'])
 cols=[col('sku','کد کالا'),col('name','کالا'),col('warehouse','انبار'),col('quantity','موجودی','qty'),col('reserved','رزرو','qty'),col('available','قابل فروش','qty'),col('unit_cost','بهای واحد','money'),col('value','ارزش','money')]
 if kind=='low': cols+=[col('min_stock','حداقل موجودی','qty'),col('shortage','کمبود','qty')]
 if kind=='dead': cols+=[col('last_out','آخرین خروج','date')]
 summ=[['ردیف‌ها',len(rows),'int'],['ارزش موجودی (بر پایه بها)',sum((x['value'] for x in rows),Decimal(0)),'money'],['کالای بدون بها',sum(1 for x in rows if x['unit_cost']<=0 and x['quantity']>0),'int']]
 if kind=='dead': summ.append([f'راکد = بدون خروج در {f.days} روز اخیر','','text'])
 return _table('گزارش انبار — '+INV_KINDS[kind],cols,rows,summ,f)

# ---------------------------------------------------------------- عملکرد بازاریاب
def _period_of(f:Flt):
 """هدف فروش فقط وقتی معنادار است که بازه داخل یک ماه میلادی باشد (Target.period = YYYY-MM)"""
 a,b=f.start,f.end
 return _month_key(a) if a and b and _month_key(a)==_month_key(b) else None
def visitors_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params)
 if not (f.start or f.end): f.start=date.today().replace(day=1);f.end=date.today()
 vq=_bounds(select(Visit).where(Visit.company_id==cid),Visit.started_at,f)
 if f.user_id: vq=vq.where(Visit.user_id==f.user_id)
 acc={}
 def A(uid): return acc.setdefault(uid,{'visits':0,'with_order':0,'out_of_range':0,'no_gps':0,'minutes':[],'customers':set(),'orders':0,'sales':Decimal(0),'leads':0,'won':0,'lost':0})
 for v in s.scalars(vq):
  a=A(v.user_id);a['visits']+=1;a['customers'].add(v.customer_id)
  if v.order_id: a['with_order']+=1
  if v.gps_status=='out_of_range': a['out_of_range']+=1
  elif v.gps_status in ('no_visit_gps','no_customer_gps'): a['no_gps']+=1
  if v.ended_at and v.started_at: a['minutes'].append((v.ended_at-v.started_at).total_seconds()/60)
 oq=_bounds(select(Order.seller_id,func.count(),func.sum(Order.total)).where(Order.company_id==cid,Order.status!='cancelled'),Order.created_at,f)
 if f.user_id: oq=oq.where(Order.seller_id==f.user_id)
 for uid,n,t in s.execute(oq.group_by(Order.seller_id)): a=A(uid);a['orders']=n;a['sales']=D(t)
 lq=select(Lead.owner_id,Lead.stage,func.count()).where(Lead.company_id==cid)
 lq=_bounds(lq,Lead.created_at,f)
 if f.user_id: lq=lq.where(Lead.owner_id==f.user_id)
 for uid,st,n in s.execute(lq.group_by(Lead.owner_id,Lead.stage)):
  a=A(uid);a['leads']+=n
  if st=='won': a['won']+=n
  elif st=='lost': a['lost']+=n
 per=_period_of(f);tg={t.user_id:D(t.sales_target) for t in s.scalars(select(Target).where(Target.company_id==cid,Target.period==per))} if per else {}
 names={u.id:u.name for u in s.scalars(select(User).where(User.id.in_(list(acc))))} if acc else {}
 rows=[]
 for uid,a in acc.items():
  t=tg.get(uid,Decimal(0));m=a['minutes']
  rows.append({'_key':str(uid),'name':names.get(uid,str(uid)),'visits':a['visits'],'customers':len(a['customers']),'with_order':a['with_order'],'conversion':_pct(a['with_order'],a['visits']),'out_of_range':a['out_of_range'],'no_gps':a['no_gps'],'avg_minutes':(Decimal(str(sum(m)/len(m)))).quantize(Q2) if m else None,'orders':a['orders'],'sales':a['sales'],'target':t if t>0 else None,'attainment':_pct(a['sales'],t) if t>0 else None,'leads':a['leads'],'won':a['won'],'lost':a['lost'],'lead_conversion':_pct(a['won'],a['won']+a['lost'])})
 rows.sort(key=lambda x:-x['sales'])
 cols=[col('name','بازاریاب'),col('visits','ویزیت','int'),col('customers','مشتری ویزیت‌شده','int'),col('with_order','ویزیت منجر به سفارش','int'),col('conversion','نرخ تبدیل ٪','pct'),col('out_of_range','خارج از شعاع','int'),col('no_gps','بدون GPS','int'),col('avg_minutes','میانگین مدت (دقیقه)','qty'),col('orders','سفارش','int'),col('sales','فروش','money'),col('target','هدف فروش','money'),col('attainment','تحقق هدف ٪','pct'),col('leads','سرنخ','int'),col('won','برنده','int'),col('lost','ازدست‌رفته','int'),col('lead_conversion','تبدیل سرنخ ٪','pct')]
 tv=sum(x['visits'] for x in rows);tw=sum(x['with_order'] for x in rows)
 return _table('عملکرد بازاریابان',cols,rows,[['کل ویزیت',tv,'int'],['نرخ تبدیل ویزیت به سفارش',_pct(tw,tv),'pct'],['فروش',sum((x['sales'] for x in rows),Decimal(0)),'money'],['هدف فروش فقط برای بازهٔ داخل یک ماه نمایش داده می‌شود','','text']],f)

# ---------------------------------------------------------------- عملکرد مأمور پخش
def drivers_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params);u,_,r=ctx
 own_only=not (has_all(r) or has_perm(r,'delivery.read.all'))
 if own_only: f.user_id=u.id
 when=func.coalesce(Delivery.delivered_at,Order.created_at)
 q=_bounds(select(Delivery,Order.total).join(Order,Order.id==Delivery.order_id).where(Delivery.company_id==cid),when,f)
 if f.user_id: q=q.where(Delivery.driver_id==f.user_id)
 acc={}
 for d,tot in s.execute(q):
  a=acc.setdefault(d.driver_id,{'total':0,'delivered':0,'failed':0,'cancelled':0,'active':0,'value':Decimal(0),'minutes':[],'out_of_range':0})
  a['total']+=1
  if d.status=='delivered':
   a['delivered']+=1;a['value']+=D(tot)
   if d.loaded_at and d.delivered_at: a['minutes'].append((d.delivered_at-d.loaded_at).total_seconds()/60)
   if d.gps_status=='out_of_range': a['out_of_range']+=1
  elif d.status=='failed': a['failed']+=1
  elif d.status=='cancelled': a['cancelled']+=1
  else: a['active']+=1
 names={x.id:x.name for x in s.scalars(select(User).where(User.id.in_(list(acc))))} if acc else {}
 rows=[]
 for did,a in acc.items():
  m=a['minutes'];rows.append({'_key':str(did),'name':names.get(did,str(did)),'total':a['total'],'delivered':a['delivered'],'failed':a['failed'],'cancelled':a['cancelled'],'active':a['active'],'success_rate':_pct(a['delivered'],a['delivered']+a['failed']),'value':a['value'],'avg_minutes':Decimal(str(sum(m)/len(m))).quantize(Q2) if m else None,'out_of_range':a['out_of_range']})
 rows.sort(key=lambda x:-x['delivered'])
 cols=[col('name','مأمور پخش'),col('total','کل ماموریت','int'),col('delivered','تحویل‌شده','int'),col('failed','ناموفق','int'),col('cancelled','لغوشده','int'),col('active','در جریان','int'),col('success_rate','نرخ موفقیت ٪','pct'),col('value','ارزش تحویل‌شده','money'),col('avg_minutes','میانگین زمان بارگیری تا تحویل (دقیقه)','qty'),col('out_of_range','تحویل خارج از شعاع','int')]
 td=sum(x['delivered'] for x in rows);tf=sum(x['failed'] for x in rows)
 return _table('عملکرد مأمورین پخش',cols,rows,[['کل ماموریت',sum(x['total'] for x in rows),'int'],['تحویل‌شده',td,'int'],['ناموفق',tf,'int'],['نرخ موفقیت',_pct(td,td+tf),'pct'],['ارزش تحویل‌شده',sum((x['value'] for x in rows),Decimal(0)),'money']],f)

# ---------------------------------------------------------------- مالی (فقط از اسناد ثبت‌شده)
def ledger_amount(s,cid,code,kind,start=None,end=None):
 q=select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).select_from(JournalLine).join(Account,Account.id==JournalLine.account_id).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,Account.code.in_(bank_codes(s,cid) if code==BANK else [code]))
 if start: q=q.where(JournalEntry.entry_date>=start)
 if end: q=q.where(JournalEntry.entry_date<=end)
 d,c=s.execute(q).one();return D(d)-D(c) if kind=='debit' else D(c)-D(d)
def type_amount(s,cid,types,start=None,end=None):
 q=select(Account.type,func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).select_from(JournalLine).join(Account,Account.id==JournalLine.account_id).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,Account.type.in_(types))
 if start: q=q.where(JournalEntry.entry_date>=start)
 if end: q=q.where(JournalEntry.entry_date<=end)
 return {t:(D(d)-D(c) if t in ('asset','expense') else D(c)-D(d)) for t,d,c in s.execute(q.group_by(Account.type))}
def finance_report(s,ctx,params):
 cid=ctx[1];f=make_filter(ctx,params);end=f.end
 pos=[('نقد و بانک',None,None),('صندوق',CASH,'debit'),('بانک',BANK,'debit'),('اسناد دریافتنی (چک)',NR,'debit'),('حساب‌های دریافتنی مشتریان',AR,'debit'),('موجودی کالا (دفتر)',INVT,'debit'),('حساب‌های پرداختنی تأمین‌کنندگان',AP,'credit'),('اسناد پرداختنی (چک)',NP,'credit'),('مالیات بر ارزش افزوده',VAT,'credit')]
 rows=[];cash=Decimal(0)
 for label,code,k in pos:
  if code is None: continue
  v=ledger_amount(s,cid,code,k,None,end);rows.append({'_key':code,'group':'وضعیت مالی تا پایان بازه','name':label,'code':code,'amount':v})
  if code in (CASH,BANK): cash+=v
 pl=type_amount(s,cid,['revenue','expense'],f.start,f.end);cg=ledger_amount(s,cid,COGS,'debit',f.start,f.end)
 rev=pl.get('revenue',Decimal(0));exp=pl.get('expense',Decimal(0))
 for label,code,v in [('درآمد دوره',None,rev),('بهای تمام‌شده',COGS,cg),('سود ناخالص',None,rev-cg),('کل هزینه‌ها',None,exp),('سود خالص',None,rev-exp)]: rows.append({'_key':code or '','group':'عملکرد دوره','name':label,'code':code or '','amount':v})
 return _table('گزارش مالی',[col('group','بخش'),col('code','کد حساب'),col('name','شرح'),col('amount','مبلغ','money')],rows,[['نقد و بانک',cash,'money'],['سود خالص دوره',rev-exp,'money'],['فقط از اسناد ثبت‌شده در دفتر؛ بدون مقدار دستی','','text']],f)
def checks_buckets(s,cid,today=None):
 """چک‌های باز (در انتظار/خوابانده‌شده) بر اساس سررسید؛ دریافتی و پرداختی جدا"""
 today=today or date.today();out={'received':{'overdue':[Decimal(0),0],'d7':[Decimal(0),0],'d30':[Decimal(0),0],'later':[Decimal(0),0]},'paid':{'overdue':[Decimal(0),0],'d7':[Decimal(0),0],'d30':[Decimal(0),0],'later':[Decimal(0),0]}}
 for c in s.scalars(select(Check).where(Check.company_id==cid,Check.status.in_(['pending','deposited']))):
  dd=(c.due_date-today).days;b=out['received' if c.kind=='received' else 'paid'];k='overdue' if dd<0 else 'd7' if dd<=7 else 'd30' if dd<=30 else 'later'
  b[k][0]+=D(c.amount);b[k][1]+=1
 return {kd:{k:{'amount':v[0],'count':v[1]} for k,v in b.items()} for kd,b in out.items()}
