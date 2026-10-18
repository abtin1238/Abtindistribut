from __future__ import annotations
from datetime import date
from decimal import Decimal
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional
from app.services.stock_batches import consume_batches
from app.core.common import D, audit, obj
from app.core.config import utcnow
from app.core.uploads import store_image
from app.core.security import has_all, has_perm
from app.models import Customer, Delivery, Invoice, Membership, Order, OrderItem, Product, Stock, StockMove, User, InvoiceLine
from app.modules.finance import add_check, payment
from app.modules.platform import MAX_UPLOAD
from app.services.notify import notify
from app.schemas import CheckIn, PaymentIn
from app.services.geo import DEFAULT_RADIUS_M, gps_check, nn_order
from app.services.accounting import make_return, post_cogs
from .schemas import DeliveryIn, DeliveryUpdate, CollectIn, BulkAssignIn

FLOW={'assigned':{'loaded','out_for_delivery','delivered','failed','cancelled'},'loaded':{'out_for_delivery','delivered','failed','cancelled'},'out_for_delivery':{'delivered','failed','cancelled'},'delivered':set(),'failed':set(),'cancelled':set()}

ACTIVE=('assigned','loaded','out_for_delivery')

def sees_all(r): return has_all(r) or has_perm(r,'delivery.read.all')

def _own(s,ctx,did,lock=False):
 u,cid,r=ctx;d=s.get(Delivery,did,with_for_update=lock)
 if not d or d.company_id!=cid or (d.driver_id!=u.id and not sees_all(r)): raise HTTPException(404,'ماموریت یافت نشد')
 return d

def _valid_signature(sig):
 if not sig: return
 if sig.startswith('data:image/png;base64,'):
  if len(sig)>300000: raise HTTPException(413,'حجم امضا بیش از حد مجاز است')
  return
 if len(sig)>200 or sig.startswith('data:'): raise HTTPException(400,'امضا باید تصویر PNG یا متن کوتاه باشد')

def _view(s,d,detail=False):
 o=s.get(Order,d.order_id);c=s.get(Customer,o.customer_id);inv=s.scalar(select(Invoice).where(Invoice.order_id==o.id))
 items=[{'product_id':p.id,'name':p.name,'sku':p.sku,'unit':p.unit,'quantity':it.quantity} for it,p in s.execute(select(OrderItem,Product).join(Product,Product.id==OrderItem.product_id).where(OrderItem.order_id==o.id).order_by(OrderItem.id)).all()]
 v={**obj(d),'order_number':o.number,'customer':{'id':c.id,'name':c.name,'phone':c.phone,'address':c.address,'lat':c.lat,'lng':c.lng},'items':items,'invoice':None}
 if inv:
  v['invoice']={'id':inv.id,'number':inv.number,'total':inv.total,'paid':inv.paid,'returned':inv.returned,'remaining':D(inv.total)-D(inv.returned)-D(inv.paid),'status':inv.status}
  if detail: v['invoice'].update({'subtotal':inv.subtotal,'tax':inv.tax,'shipping':inv.shipping,'note':inv.note or '','terms':inv.terms or ''})
  if detail: v['invoice_lines']=[obj(l) for l in s.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id==inv.id).order_by(InvoiceLine.id))]
 return v

def assign_delivery(oid: int, x: DeliveryIn, ctx, s: Session):
 u,cid,r=ctx;o=s.get(Order,oid);d=s.get(User,x.driver_id)
 if not o or o.company_id!=cid or not d:raise HTTPException(404,'سفارش/مامور یافت نشد')
 if not s.scalar(select(Membership).where(Membership.user_id==d.id,Membership.company_id==cid)): raise HTTPException(400,'مامور متعلق به این شرکت نیست')
 if o.status not in ('confirmed','assigned'): raise HTTPException(400,'سفارش آماده تخصیص نیست')
 existing=s.scalar(select(Delivery).where(Delivery.order_id==oid,Delivery.company_id==cid,Delivery.status.not_in(['failed','cancelled','delivered'])))
 if existing: return obj(existing)
 z=Delivery(company_id=cid,order_id=oid,driver_id=d.id);s.add(z);o.status='assigned';notify(s,cid,[d.id],'delivery_new','ماموریت جدید',f'سفارش {o.number} برای شما تخصیص یافت','delivery',z.id);audit(s,cid,u.id,'assign','delivery',z.id);s.commit();s.refresh(z);return obj(z)

def bulk_assign(x: BulkAssignIn, ctx, s: Session):
 """تخصیص چند سفارش به یک مأمور؛ هر سفارش مستقل است و نتیجه‌ی تک‌تک برگردانده می‌شود."""
 res=[]
 for oid in dict.fromkeys(x.order_ids):
  try: res.append({'order_id':oid,'status':'ok','delivery_id':assign_delivery(oid,DeliveryIn(order_id=oid,driver_id=x.driver_id),ctx,s)['id']})
  except HTTPException as e: s.rollback();res.append({'order_id':oid,'status':'error','detail':str(e.detail)})
 return {'assigned':sum(r['status']=='ok' for r in res),'results':res}

def board(status: Optional[str], day: Optional[date], driver_id: Optional[int], ctx, s: Session):
 """نمای مدیر: ماموریت‌ها با نام مشتری/مأمور؛ سفارش‌های تأییدشده‌ی بدون ماموریت در `unassigned`."""
 u,cid,r=ctx
 if not sees_all(r): raise HTTPException(403,'دسترسی کافی نیست')
 q=select(Delivery,Order,Customer,User).join(Order,Order.id==Delivery.order_id).join(Customer,Customer.id==Order.customer_id).join(User,User.id==Delivery.driver_id).where(Delivery.company_id==cid)
 if status: q=q.where(Delivery.status==status)
 if driver_id: q=q.where(Delivery.driver_id==driver_id)
 rows=[(d,o,c,dr) for d,o,c,dr in s.execute(q.order_by(Delivery.id.desc()).limit(500)).all() if not day or ((d.delivered_at or o.created_at).date()==day)]
 busy=select(Delivery.order_id).where(Delivery.company_id==cid,Delivery.status.in_(ACTIVE))
 un=s.execute(select(Order,Customer).join(Customer,Customer.id==Order.customer_id).where(Order.company_id==cid,Order.status=='confirmed',Order.id.not_in(busy)).order_by(Order.id).limit(200)).all()
 return {'deliveries':[{**obj(d),'order_number':o.number,'customer_name':c.name,'driver_name':dr.name} for d,o,c,dr in rows],'unassigned':[{'order_id':o.id,'number':o.number,'customer_name':c.name,'total':o.total} for o,c in un]}

def deliveries(ctx, s: Session):
 u,cid,r=ctx;q=select(Delivery).where(Delivery.company_id==cid)
 if not sees_all(r): q=q.where(Delivery.driver_id==u.id)
 return [obj(x) for x in s.scalars(q.order_by(Delivery.id.desc())).all()]

def my_deliveries(day: Optional[date], lat: Optional[float], lng: Optional[float], ctx, s: Session):
 """ماموریت‌های فعال + انجام‌شده‌ی روز `day`؛ فعال‌ها به ترتیب مسیر (نزدیک‌ترین همسایه از نقطه‌ی فعلی)"""
 u,cid,r=ctx;day=day or date.today()
 rows=s.scalars(select(Delivery).where(Delivery.company_id==cid,Delivery.driver_id==u.id).order_by(Delivery.id)).all()
 act=[_view(s,d) for d in rows if d.status in ACTIVE];done=[_view(s,d) for d in rows if d.status=='delivered' and d.delivered_at and d.delivered_at.date()==day]
 for v in act: v['_k']={'id':v['id'],'lat':v['customer']['lat'],'lng':v['customer']['lng']}
 order=nn_order([v['_k'] for v in act],(lat,lng) if lat is not None and lng is not None else None);pos={k['id']:i for i,k in enumerate(order,1)}
 for v in act: v.pop('_k');v['stop']=pos[v['id']]
 act.sort(key=lambda v:v['stop']);return {'active':act,'done':done}

def delivery_detail(did: int, ctx, s: Session):
 return _view(s, _own(s, ctx, did), True)

async def delivery_photo(did: int, file: UploadFile, ctx, s: Session):
 u,cid,r=ctx;d=_own(s,ctx,did)
 if d.driver_id!=u.id and not has_all(r): raise HTTPException(403,'این ماموریت متعلق به شما نیست')
 data=await file.read(MAX_UPLOAD+1);doc,size=store_image(s,cid,'delivery',d.id,data,MAX_UPLOAD);d.proof_photo=f'/api/documents/{doc.id}/download'
 audit(s,cid,u.id,'photo','delivery',d.id,{'document_id':doc.id,'size':size});s.commit();return {'id':d.id,'proof_photo':d.proof_photo,'document_id':doc.id}

def collect(did: int, x: CollectIn, ctx, s: Session):
 """وصول وجه/چک در محل؛ فقط روی ماموریت خود راننده. نقد/کارت/حواله به فاکتور تخصیص می‌یابد و سند می‌سازد؛ چک مثل ثبت چک عادی ثبت می‌شود (تخصیص به فاکتور ندارد)."""
 u,cid,r=ctx;d=_own(s,ctx,did,True)
 if d.driver_id!=u.id and not has_all(r): raise HTTPException(403,'این ماموریت متعلق به شما نیست')
 if d.status in ('failed','cancelled'): raise HTTPException(409,'برای ماموریت ناموفق/لغوشده وصول مجاز نیست')
 o=s.get(Order,d.order_id);c=s.get(Customer,o.customer_id);inv=s.scalar(select(Invoice).where(Invoice.order_id==o.id))
 if not inv or inv.status=='cancelled': raise HTTPException(409,'فاکتور معتبر وجود ندارد')
 if x.method=='check':
  if not x.check_number.strip() or not x.due_date: raise HTTPException(400,'شماره و سررسید چک الزامی است')
  if x.amount>D(inv.total)-D(inv.returned)-D(inv.paid): raise HTTPException(400,'مبلغ چک بیشتر از مانده فاکتور است')
  return {'kind':'check','record':add_check(CheckIn(number=x.check_number.strip(),kind='received',amount=x.amount,due_date=x.due_date,bank=x.bank,party=c.name,notes=f'وصول در محل — ماموریت {d.id}، فاکتور {inv.number}',customer_id=c.id),ctx,s)}
 if x.method not in ('cash','card','transfer'): raise HTTPException(400,'روش پرداخت نامعتبر است')
 return {'kind':'payment','record':payment(PaymentIn(customer_id=c.id,invoice_id=inv.id,amount=x.amount,kind='receipt',method=x.method,reference=x.reference or f'delivery-{d.id}'),ctx,s)}

def update_delivery(did: int, x: DeliveryUpdate, ctx, s: Session):
 u,cid,r=ctx;d=s.get(Delivery,did,with_for_update=True)
 if not d or d.company_id!=cid: raise HTTPException(404,'ماموریت یافت نشد')
 if d.driver_id!=u.id and '*' not in (r.permissions or []): raise HTTPException(403,'این ماموریت متعلق به شما نیست')
 if x.status not in FLOW: raise HTTPException(400,'وضعیت نامعتبر')
 if x.status==d.status: return obj(d)   # تکرار (مثلاً همگام‌سازی دوباره) بی‌اثر است
 if x.status not in FLOW[d.status]: raise HTTPException(409,f'انتقال از {d.status} به {x.status} مجاز نیست')
 if x.status=='cancelled' and not (has_all(r) or has_perm(r,'delivery.assign')): raise HTTPException(403,'لغو ماموریت مجاز نیست')
 if x.status=='failed' and not x.reason.strip(): raise HTTPException(400,'دلیل عدم تحویل الزامی است')
 _valid_signature(x.signature)
 o=s.get(Order,d.order_id);d.status=x.status
 if x.lat is not None: d.lat=x.lat
 if x.lng is not None: d.lng=x.lng
 if x.reason: d.reason=x.reason
 if x.signature: d.signature=x.signature
 if x.proof_photo: d.proof_photo=x.proof_photo
 if x.status=='loaded': d.loaded_at=utcnow()
 if x.status=='delivered':
  c=s.get(Customer,o.customer_id);d.distance_m,d.gps_status=gps_check(x.lat,x.lng,c.lat,c.lng,DEFAULT_RADIUS_M)
  d.delivered_at=utcnow()
  if o.status!='delivered':
   oitems=s.scalars(select(OrderItem).where(OrderItem.order_id==o.id)).all();got={}
   if x.items is not None:
    ordered={it.product_id:D(it.quantity) for it in oitems}
    for di in x.items:
     if di.product_id not in ordered or D(di.quantity)>ordered[di.product_id]: raise HTTPException(400,'مقدار تحویل‌شده نامعتبر است')
     got[di.product_id]=D(di.quantity)
    if any(got.get(it.product_id,Decimal(0))<D(it.quantity) for it in oitems) and not x.reason.strip(): raise HTTPException(400,'دلیل تحویل ناقص الزامی است')
   o.status='delivered';short=[];issued=[]
   for it in oitems:
    q=got.get(it.product_id,Decimal(0)) if x.items is not None else D(it.quantity)
    st=s.scalar(select(Stock).where(Stock.warehouse_id==o.warehouse_id,Stock.product_id==it.product_id).with_for_update())
    if not st or st.quantity<q or st.reserved<it.quantity: raise HTTPException(409,'موجودی رزروشده با تحویل سازگار نیست')
    st.quantity-=q;st.reserved-=it.quantity
    if q>0: s.add(StockMove(company_id=cid,warehouse_id=o.warehouse_id,product_id=it.product_id,kind='out',quantity=q,unit_cost=s.get(Product,it.product_id).avg_cost,reference=o.number,reason='تحویل سفارش',user_id=u.id));issued.append((it.product_id,q));consume_batches(s,cid,o.warehouse_id,it.product_id,q)
    if q<D(it.quantity): short.append((it.product_id,D(it.quantity)-q))
   inv=s.scalar(select(Invoice).where(Invoice.order_id==o.id))
   if inv: post_cogs(s,cid,u.id,inv,issued)   # بهای تمام‌شده فقط برای مقدار واقعاً تحویل‌شده
   if short:
    if inv: make_return(s,cid,u.id,o,inv,short,'تحویل ناقص: '+(x.reason or ''),False)
 if x.status in ('failed','cancelled'):
  # رزرو انبار حفظ می‌شود تا سفارش دوباره تخصیص یابد؛ برای آزادسازی، سفارش را لغو کنید
  if o.status=='assigned': o.status='confirmed'
  if x.status=='failed': notify(s,cid,[o.seller_id],'delivery_failed','عدم تحویل',f'سفارش {o.number}: {x.reason.strip()}','delivery',d.id)
 if x.status=='delivered': notify(s,cid,[o.seller_id],'delivery_done','تحویل موفق',f'سفارش {o.number} تحویل شد','delivery',d.id)
 audit(s,cid,u.id,'delivery_update','delivery',did,x.model_dump(exclude={'signature'}));s.commit();return obj(d)

def report_delivery(start: Optional[date], end: Optional[date], driver_id: Optional[int], ctx, s: Session):
 if start and end and start>end: raise HTTPException(400,'بازه‌ی تاریخ نامعتبر است')
 q=select(Delivery,Order.created_at).join(Order,Order.id==Delivery.order_id).where(Delivery.company_id==ctx[1])
 if driver_id is not None: q=q.where(Delivery.driver_id==driver_id)
 rows=[(d,c) for d,c in s.execute(q).all() if (not start or (d.delivered_at or c).date()>=start) and (not end or (d.delivered_at or c).date()<=end)]
 ds=[d for d,_ in rows]
 return {'start':start,'end':end,'total':len(ds),'delivered':sum(x.status=='delivered' for x in ds),'failed':sum(x.status=='failed' for x in ds),'cancelled':sum(x.status=='cancelled' for x in ds),'active':sum(x.status in ACTIVE for x in ds)}
