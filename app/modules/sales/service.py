from __future__ import annotations
from datetime import date
from decimal import Decimal
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.common import ESC, D, audit, like_pat, num, obj, same_company
from app.core.paging import page_rows
from app.core.security import has_all, has_perm, own_orders, wh_check, wh_scope
from app.models import Company, Customer, Delivery, Invoice, InvoiceLine, Order, OrderItem, Payment, Product, SalesReturn, Stock, User, Warehouse, Setting
from app.modules.platform import brand_dict
from app.services.units import to_base_qty
from app.services.notify import notify, users_with_perm
from app.services.accounting import INVOICE_FLOW, effective_price, invoice_lines, make_return, party_balance, post_entry, reverse_entry, set_invoice_status, source_entry, vat_percent
from .schemas import OrderIn, InvoiceNoteIn, ReturnIn

def invoice_terms(s,cid):
 return s.scalar(select(Setting.value).where(Setting.company_id==cid,Setting.key=='invoice_terms')) or ''

def _invoice_access(s,ctx,iid,write=False):
 u,cid,r=ctx;inv=same_company(s,Invoice,iid,cid);o=s.get(Order,inv.order_id)
 if write:
  if not has_all(r) and o.seller_id!=u.id: raise HTTPException(404,'رکورد یافت نشد')
 elif not has_all(r) and o.seller_id!=u.id and not s.scalar(select(Delivery.id).where(Delivery.order_id==o.id,Delivery.driver_id==u.id)): raise HTTPException(404,'رکورد یافت نشد')
 wh_check(s,ctx,o.warehouse_id);return inv,o

def create_order(x: OrderIn, ctx, s: Session):
 u,cid,r=ctx; c=s.get(Customer,x.customer_id); w=s.get(Warehouse,x.warehouse_id)
 if not c or c.company_id!=cid or not w or w.company_id!=cid: raise HTTPException(404,'مشتری یا انبار یافت نشد')
 wh_check(s,ctx,w.id)
 if not x.items: raise HTTPException(400,'سفارش بدون کالا مجاز نیست')
 total=Decimal('0'); prepared=[]
 for it in x.items:
  it.quantity=to_base_qty(s,cid,it.product_id,it.unit,it.quantity);it.unit=''   # همه‌چیز از اینجا به بعد به واحد پایه
  p=s.get(Product,it.product_id);st=s.scalar(select(Stock).where(Stock.warehouse_id==w.id,Stock.product_id==it.product_id).with_for_update())
  if not p or p.company_id!=cid or it.quantity<=0 or not st or st.quantity-st.reserved<it.quantity: raise HTTPException(400,f'موجودی کافی نیست: {p.name if p else it.product_id}')
  price=effective_price(s,cid,p.id,c.customer_group,it.quantity)
  if it.discount<0 or (it.discount>0 and not has_perm(r,'pricing.write')): raise HTTPException(403,'اعمال تخفیف دستی مجاز نیست')
  discount=it.discount; line=it.quantity*price-discount
  cap=getattr(r,'max_discount_percent',None)
  if discount>0 and cap is not None and '*' not in (r.permissions or []) and discount>(it.quantity*price*D(cap)/Decimal(100)): raise HTTPException(403,f'تخفیف دستی از سقف مجاز نقش شما ({D(cap):g}٪ مبلغ قلم) بیشتر است')
  if line<0: raise HTTPException(400,'تخفیف از مبلغ قلم بیشتر است')
  total+=line;prepared.append((p,it,price))
 if c.credit_limit and party_balance(s,cid,'customer',c.id)+total>c.credit_limit: raise HTTPException(400,'سقف اعتباری مشتری مجاز نیست')
 o=Order(company_id=cid,number=num('SO',Order,s),customer_id=c.id,seller_id=u.id,warehouse_id=w.id,total=total,shipping=x.shipping,note=x.note);s.add(o);s.flush()
 for p,it,price in prepared:s.add(OrderItem(order_id=o.id,product_id=p.id,quantity=it.quantity,unit_price=price,discount=it.discount))
 audit(s,cid,u.id,'create','order',o.id,{'number':o.number});notify(s,cid,[x for x in users_with_perm(s,cid,'sales.approve') if x!=u.id],'order_new','سفارش جدید '+o.number,f'مشتری {c.name} — مبلغ {total:,.0f}','order',o.id);s.commit();return obj(o)

def approve_order(oid: int, ctx, s: Session):
 u,cid,r=ctx;o=s.get(Order,oid,with_for_update=True)
 if not o or o.company_id!=cid: raise HTTPException(404,'سفارش یافت نشد')
 if not has_all(r) and o.seller_id!=u.id: raise HTTPException(404,'سفارش یافت نشد')
 wh_check(s,ctx,o.warehouse_id)
 if o.status!='draft': raise HTTPException(400,'وضعیت سفارش معتبر نیست')
 items=s.scalars(select(OrderItem).where(OrderItem.order_id==o.id)).all()
 for it in items:
  st=s.scalar(select(Stock).where(Stock.warehouse_id==o.warehouse_id,Stock.product_id==it.product_id).with_for_update())
  if not st or st.quantity-st.reserved<it.quantity: raise HTTPException(400,'موجودی برای رزرو کافی نیست')
  st.reserved+=it.quantity
 sub=o.total;tax=(sub*vat_percent(s,cid)/Decimal(100)).quantize(Decimal('0.01'));grand=sub+tax+o.shipping;o.status='confirmed';inv=Invoice(company_id=cid,order_id=o.id,number=num('INV',Invoice,s),subtotal=sub,tax=tax,shipping=o.shipping,total=grand,note=o.note or '',terms=invoice_terms(s,cid));s.add(inv);s.flush();post_entry(s,cid,u.id,f'فاکتور فروش {inv.number}',invoice_lines(inv,o.customer_id,sum((D(it.discount) for it in items),Decimal(0))),source=('invoice',inv.id))
 for it in items:
  pr=s.get(Product,it.product_id);s.add(InvoiceLine(invoice_id=inv.id,product_id=it.product_id,description=pr.name,unit=pr.unit,quantity=it.quantity,unit_price=it.unit_price,discount=it.discount,line_total=it.quantity*it.unit_price-it.discount))
 audit(s,cid,u.id,'approve','order',o.id)
 if o.seller_id!=u.id: notify(s,cid,[o.seller_id],'invoice_approved',f'فاکتور {inv.number} تأیید شد',f'سفارش {o.number}','invoice',inv.id)
 s.commit();return obj(o)

def orders(response: Response, limit: int, offset: int, ctx, s: Session):
 u,cid,r=ctx;q=select(Order).where(Order.company_id==cid);q=q if has_all(r) else q.where(own_orders(u))
 sc=wh_scope(s,ctx)
 if sc is not None: q=q.where(Order.warehouse_id.in_(sc))
 return [obj(x) for x in page_rows(s,q.order_by(Order.id),response,limit,offset)]

def invoices(status: str, q: str, start: date | None, end: date | None, limit: int, ctx, s: Session):
 u,cid,r=ctx
 if status and status not in INVOICE_FLOW: raise HTTPException(400,'وضعیت فاکتور نامعتبر است')
 stmt=select(Invoice,Order,Customer).join(Order,Order.id==Invoice.order_id).join(Customer,Customer.id==Order.customer_id).where(Invoice.company_id==cid)
 if not has_all(r): stmt=stmt.where(Invoice.order_id.in_(select(Order.id).where(own_orders(u))))
 sc=wh_scope(s,ctx)
 if sc is not None: stmt=stmt.where(Order.warehouse_id.in_(sc))
 if status: stmt=stmt.where(Invoice.status==status)
 if start: stmt=stmt.where(func.date(Invoice.issued_at)>=start)
 if end: stmt=stmt.where(func.date(Invoice.issued_at)<=end)
 if q.strip():
  pat=like_pat(q.strip());stmt=stmt.where((Invoice.number.ilike(pat,escape=ESC))|(Customer.name.ilike(pat,escape=ESC))|(Order.number.ilike(pat,escape=ESC)))
 out=[]
 for inv,o,c in s.execute(stmt.order_by(Invoice.id.desc()).limit(limit)):
  d=obj(inv);d.update({'order_number':o.number,'order_status':o.status,'customer_id':c.id,'customer_name':c.name,'remaining':inv.total-inv.returned-inv.paid});out.append(d)
 return out

def invoice_note(iid: int, x: InvoiceNoteIn, ctx, s: Session):
 u,cid,r=ctx;inv,o=_invoice_access(s,ctx,iid,True)
 if inv.status=='cancelled': raise HTTPException(409,'یادداشت فاکتور باطل‌شده قابل ویرایش نیست')
 inv.note=x.note;o.note=x.note;audit(s,cid,u.id,'note','invoice',inv.id);s.commit();return {'id':inv.id,'note':inv.note}

def invoice_detail(iid: int, ctx, s: Session):
 u,cid,r=ctx;inv,o=_invoice_access(s,ctx,iid)
 lines=[obj(x) for x in s.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id==inv.id).order_by(InvoiceLine.id))]
 if not lines:
  for it in s.scalars(select(OrderItem).where(OrderItem.order_id==o.id)):
   pr=s.get(Product,it.product_id);lines.append({'product_id':it.product_id,'description':pr.name,'unit':pr.unit,'quantity':it.quantity,'unit_price':it.unit_price,'discount':it.discount,'line_total':it.quantity*it.unit_price-it.discount})
 c=s.get(Customer,o.customer_id);co=s.get(Company,cid);w=s.get(Warehouse,o.warehouse_id);sl=s.get(User,o.seller_id)
 pays=[{'id':x.id,'amount':x.amount,'method':x.method,'created_at':x.created_at} for x in s.scalars(select(Payment).where(Payment.company_id==cid,Payment.invoice_id==inv.id).order_by(Payment.id))]
 return {'invoice':obj(inv),'lines':lines,'order_number':o.number,'customer':{'name':c.name,'code':c.code,'phone':c.phone,'address':c.address,'region':c.region,'customer_group':c.customer_group},'company':{'name':co.name,'code':co.code,'brand':brand_dict(s,cid)},'warehouse':w.name if w else '','seller':sl.name if sl else '','payments':pays,'returns':[{'number':x.number,'total':x.total,'reason':x.reason,'created_at':x.created_at} for x in s.scalars(select(SalesReturn).where(SalesReturn.company_id==cid,SalesReturn.invoice_id==inv.id).order_by(SalesReturn.id))],'order_status':o.status,'order_id':o.id,'customer_id':c.id,'remaining':inv.total-inv.returned-inv.paid}

def invoice_pdf(iid: int, ctx, s: Session):
 from app.services.exporters import invoice_pdf as _pdf
 d=invoice_detail(iid=iid,ctx=ctx,s=s);d['invoice']['terms']=d['invoice'].get('terms') or invoice_terms(s,ctx[1])
 try: return _pdf(d),d['invoice']['number']
 except RuntimeError as e: raise HTTPException(503,str(e))

def report_sales(start: date, end: date, ctx, s: Session):
 rows=s.scalars(select(Order).where(Order.company_id==ctx[1],func.date(Order.created_at)>=start,func.date(Order.created_at)<=end)).all();return {'start':start,'end':end,'orders':len(rows),'total':sum((x.total for x in rows),Decimal(0)),'by_status':{st:sum((x.total for x in rows if x.status==st),Decimal(0)) for st in {x.status for x in rows}}}

def cancel_order(oid: int, ctx, s: Session):
 u,cid,r=ctx;same_company(s,Order,oid,cid);o=s.get(Order,oid,with_for_update=True)
 if not has_all(r) and o.seller_id!=u.id: raise HTTPException(404,'سفارش یافت نشد')
 if o.status in ('delivered','cancelled'): raise HTTPException(400,'این سفارش قابل لغو نیست؛ برای سفارش تحویل‌شده از برگشت از فروش استفاده کنید')
 if o.status in ('confirmed','assigned'):
  inv=s.scalar(select(Invoice).where(Invoice.order_id==o.id))
  if inv and inv.paid>0: raise HTTPException(400,'ابتدا پرداخت‌های فاکتور باید برگشت داده شود')
  for it in s.scalars(select(OrderItem).where(OrderItem.order_id==o.id)):
   st=s.scalar(select(Stock).where(Stock.warehouse_id==o.warehouse_id,Stock.product_id==it.product_id).with_for_update())
   if st: st.reserved=max(Decimal(0),st.reserved-it.quantity)
  if inv:
   je=source_entry(s,cid,'invoice',inv.id)
   if je and je.status!='reversed': reverse_entry(s,cid,u.id,je,'لغو سفارش')
   set_invoice_status(inv,'cancelled')
  for d in s.scalars(select(Delivery).where(Delivery.order_id==o.id,Delivery.status.in_(['assigned','out_for_delivery']))): d.status='cancelled'
 o.status='cancelled';audit(s,cid,u.id,'cancel','order',o.id);s.commit();return obj(o)

def return_order(oid: int, x: ReturnIn, ctx, s: Session):
 u,cid,r=ctx;o=same_company(s,Order,oid,cid)
 if o.status!='delivered': raise HTTPException(409,'برگشت از فروش فقط برای سفارش تحویل‌شده ممکن است')
 inv=s.scalar(select(Invoice).where(Invoice.order_id==o.id,Invoice.company_id==cid))
 if not inv or inv.status=='cancelled': raise HTTPException(409,'فاکتور معتبر وجود ندارد')
 rt=make_return(s,cid,u.id,o,inv,[(i.product_id,i.quantity) for i in x.items],x.reason,True);audit(s,cid,u.id,'return','order',o.id,x.model_dump());s.commit();return obj(rt)

def sales_returns(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(SalesReturn).where(SalesReturn.company_id == ctx[1]).order_by(SalesReturn.id.desc()).limit(500))]
