from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D, Q2, audit, list_page, num, obj
from app.core.paging import page_rows
from app.core.security import wh_check, wh_scope
from app.models import CostAllocation, Product, Purchase, PurchaseItem, Stock, StockMove, Supplier, Warehouse
from app.services.accounting import AP, INVT, apply_receipt_cost, apply_return_cost, party_balances, post_entry, purchase_lines
from app.services.units import to_base_cost, to_base_qty
from app.services.costing import allocate_freight, line_unit_cost
from app.services.stock_batches import add_batch, consume_batches
from .schemas import CostAllocationIn, PurchaseIn, PurchaseReceiptIn, PurchaseReturnIn

def suppliers(response: Response, limit: int, offset: int, ctx, s: Session):
 b=party_balances(s,ctx[1],'supplier');return [{**obj(x),'balance':b.get(x.id,Decimal(0))} for x in list_page(s,Supplier,ctx[1],response,limit,offset)]

def add_supplier(payload: dict, ctx, s: Session):
 u,cid,r=ctx
 name=str(payload.get('name') or '').strip();phone=str(payload.get('phone') or '').strip()
 if not name: raise HTTPException(400,'نام تأمین‌کننده الزامی است')
 if len(name)>200 or len(phone)>50: raise HTTPException(400,'طول نام یا تلفن بیش از حد مجاز است')
 q=Supplier(company_id=cid,name=name,phone=phone);s.add(q);audit(s,cid,u.id,'create','supplier');s.commit();s.refresh(q);return obj(q)

def purchases(response: Response, limit: int, offset: int, ctx, s: Session):
 st=select(Purchase).where(Purchase.company_id==ctx[1]).order_by(Purchase.id);sc=wh_scope(s,ctx)
 if sc is not None: st=st.where(Purchase.warehouse_id.in_(sc))
 rows=page_rows(s,st,response,limit,offset)
 sn={x.id:x.name for x in s.scalars(select(Supplier).where(Supplier.company_id==ctx[1]))};wn={x.id:x.name for x in s.scalars(select(Warehouse).where(Warehouse.company_id==ctx[1]))}
 return [{**obj(x),'supplier_name':sn.get(x.supplier_id,''),'warehouse_name':wn.get(x.warehouse_id,'')} for x in rows]

def purchase_detail(pid: int, ctx, s: Session):
 p=s.get(Purchase,pid)
 if not p or p.company_id!=ctx[1]: raise HTTPException(404,'خرید یافت نشد')
 wh_check(s,ctx,p.warehouse_id)
 items=s.scalars(select(PurchaseItem).where(PurchaseItem.purchase_id==p.id).order_by(PurchaseItem.id)).all()
 names={x.id:x.name for x in s.scalars(select(Product).where(Product.id.in_([i.product_id for i in items]))).all()} if items else {}
 return {**obj(p),'items':[{**obj(i),'product':names.get(i.product_id,'')} for i in items]}

def create_purchase(x: PurchaseIn, ctx, s: Session):
 u,cid,r=ctx; sup=s.get(Supplier,x.supplier_id);w=s.get(Warehouse,x.warehouse_id)
 if not sup or sup.company_id!=cid or not w or w.company_id!=cid: raise HTTPException(404,'تأمین‌کننده یا انبار نامعتبر')
 wh_check(s,ctx,w.id)
 if not x.items: raise HTTPException(400,'خرید بدون کالا مجاز نیست')
 nets=[]
 for it in x.items:
  prod=s.get(Product,it.product_id)
  if not prod or prod.company_id!=cid: raise HTTPException(404,'کالای خرید نامعتبر')
  if (it.unit or '').strip():   # واحد فرعی ← واحد پایه (تعداد × ضریب، بها ÷ ضریب)
   it.unit_cost=to_base_cost(s,cid,it.product_id,it.unit,it.unit_cost);it.quantity=to_base_qty(s,cid,it.product_id,it.unit,it.quantity);it.unit=''
  gross=(it.quantity*it.unit_cost).quantize(Q2)
  if it.discount>gross: raise HTTPException(400,'تخفیف از مبلغ قلم بیشتر است')
  if prod.track_batch and not it.batch_no.strip(): raise HTTPException(400,f'کالای «{prod.name}» بچ‌دار است؛ شماره بچ الزامی است')
  nets.append(gross-it.discount)
 shares=allocate_freight(nets,[it.quantity for it in x.items],x.freight)
 total=sum(nets,Decimal(0))+x.freight; p=Purchase(company_id=cid,number=num('PUR',Purchase,s),supplier_id=sup.id,warehouse_id=w.id,total=total,discount=sum((it.discount for it in x.items),Decimal(0)),freight=x.freight);s.add(p);s.flush()
 for it,sh in zip(x.items,shares): s.add(PurchaseItem(purchase_id=p.id,product_id=it.product_id,quantity=it.quantity,unit_cost=it.unit_cost,discount=it.discount,landed=sh,batch_no=it.batch_no.strip(),expiry_date=it.expiry_date))
 audit(s,cid,u.id,'create','purchase',p.id);s.commit();return obj(p)

def receive_purchase(pid: int, ctx, s: Session, x: PurchaseReceiptIn | None = None):
 """رسید کامل یا جزئی. x.items خالی = دریافت همهٔ باقیمانده. هر رسید موجودی، میانگین بها و سند (بدهکار موجودی/بستانکار تأمین‌کننده) می‌سازد؛ آخرین رسید باقی‌ماندهٔ گرد‌کردن را می‌گیرد تا جمع اسناد = جمع خرید."""
 u,cid,r=ctx;p=s.get(Purchase,pid,with_for_update=True)
 if p: wh_check(s,ctx,p.warehouse_id)
 if not p or p.company_id!=cid: raise HTTPException(404,'خرید یافت نشد')
 if p.status in ('received','cancelled'): raise HTTPException(400 if p.status=='received' else 409,'خرید قبلاً دریافت شده' if p.status=='received' else 'خرید لغو شده است')
 items=s.scalars(select(PurchaseItem).where(PurchaseItem.purchase_id==p.id).order_by(PurchaseItem.id).with_for_update()).all()
 want={}
 if x and x.items:
  for ri in x.items:
   if ri.product_id in want: raise HTTPException(400,'کالای تکراری در رسید')
   want[ri.product_id]=D(ri.quantity)
  unknown=set(want)-{i.product_id for i in items}
  if unknown: raise HTTPException(404,'کالا در این خرید نیست')
 value=Decimal(0);got=False
 for it in items:
  rem=D(it.quantity)-D(it.received_qty);q=want.get(it.product_id,Decimal(0)) if want else rem
  if q<=0: continue
  if q>rem: raise HTTPException(400,'مقدار رسید از باقیماندهٔ سفارش بیشتر است')
  got=True;prod=s.get(Product,it.product_id,with_for_update=True);unit=line_unit_cost(it.quantity,D(it.quantity)*D(it.unit_cost),it.discount,it.landed)
  apply_receipt_cost(s,prod,q,unit)   # قبل از افزودن به موجودی (وزن موجودی قبلی)
  st=s.scalar(select(Stock).where(Stock.warehouse_id==p.warehouse_id,Stock.product_id==it.product_id).with_for_update()) or Stock(warehouse_id=p.warehouse_id,product_id=it.product_id,quantity=0,reserved=0);s.add(st);st.quantity+=q;s.add(StockMove(company_id=cid,warehouse_id=p.warehouse_id,product_id=it.product_id,kind='purchase_in',quantity=q,unit_cost=unit,reference=p.number,reason='رسید خرید',user_id=u.id))
  if it.batch_no: add_batch(s,cid,p.warehouse_id,it.product_id,q,it.batch_no,it.expiry_date)
  it.received_qty=D(it.received_qty)+q;value+=(q*unit).quantize(Q2)
 if not got: raise HTTPException(400,'مقداری برای دریافت مشخص نشده یا چیزی باقی نمانده')
 done=all(D(i.received_qty)>=D(i.quantity) for i in items)
 if done: value=D(p.total)-D(p.received_value)   # باقی‌ماندهٔ گرد‌کردن به آخرین رسید
 p.received_value=D(p.received_value)+value;p.status='received' if done else 'partial'
 post_entry(s,cid,u.id,f'رسید خرید {p.number}'+('' if done else ' (جزئی)'),[{'code':INVT,'debit':value},{'code':AP,'credit':value,'supplier_id':p.supplier_id}],source=('purchase_receipt',p.id) if not done or D(p.received_value)!=value else ('purchase',p.id));audit(s,cid,u.id,'receive','purchase',p.id,{'value':str(value),'partial':not done});s.commit();return obj(p)

def cancel_purchase(pid: int, ctx, s: Session):
 """لغو سفارش خرید: فقط پیش‌نویس بدون هیچ رسید؛ سند و موجودی ندارد."""
 u,cid,r=ctx;p=s.get(Purchase,pid,with_for_update=True)
 if p: wh_check(s,ctx,p.warehouse_id)
 if not p or p.company_id!=cid: raise HTTPException(404,'خرید یافت نشد')
 if p.status!='draft' or D(p.received_value)>0: raise HTTPException(409,'فقط خرید پیش‌نویس و بدون رسید قابل لغو است؛ پس از رسید از «برگشت از خرید» استفاده کنید')
 p.status='cancelled';audit(s,cid,u.id,'cancel','purchase',p.id);s.commit();return obj(p)

def allocate_cost(pid: int, x: CostAllocationIn, ctx, s: Session):
 """تسهیم هزینهٔ جانبی (گمرک/حمل/بیمه) روی اقلام یک خرید پیش از اولین رسید؛ به بهای تمام‌شده و مبلغ خرید افزوده می‌شود. basis: value=به نسبت ارزش خالص، qty=به نسبت تعداد."""
 u,cid,r=ctx;p=s.get(Purchase,pid,with_for_update=True)
 if p: wh_check(s,ctx,p.warehouse_id)
 if not p or p.company_id!=cid: raise HTTPException(404,'خرید یافت نشد')
 if p.status!='draft' or D(p.received_value)>0: raise HTTPException(409,'تسهیم هزینه فقط پیش از اولین رسید ممکن است')
 items=s.scalars(select(PurchaseItem).where(PurchaseItem.purchase_id==p.id).order_by(PurchaseItem.id).with_for_update()).all()
 if not items: raise HTTPException(400,'خرید بدون قلم است')
 nets=[(D(i.quantity)*D(i.unit_cost)).quantize(Q2)-D(i.discount) for i in items] if x.basis=='value' else [Decimal(0)]*len(items)
 shares=allocate_freight(nets,[i.quantity for i in items],x.amount)
 for i,sh in zip(items,shares): i.landed=D(i.landed)+sh
 p.total=D(p.total)+D(x.amount);p.freight=D(p.freight)+D(x.amount)
 a=CostAllocation(company_id=cid,purchase_id=p.id,label=x.label,basis=x.basis,amount=x.amount,created_by=u.id);s.add(a)
 audit(s,cid,u.id,'allocate_cost','purchase',p.id,{'label':x.label,'amount':str(x.amount),'basis':x.basis});s.commit();return {**obj(p),'allocated':str(x.amount),'shares':[str(v) for v in shares]}

def return_purchase(pid: int, x: PurchaseReturnIn, ctx, s: Session):
 """برگشت از خرید: کاهش موجودی انبار، کاهش بدهی تأمین‌کننده با همان بهای رسید و بازمحاسبهٔ میانگین بهای کالا"""
 u,cid,r=ctx;p=s.get(Purchase,pid,with_for_update=True)
 if p: wh_check(s,ctx,p.warehouse_id)
 if not p or p.company_id!=cid: raise HTTPException(404,'خرید یافت نشد')
 if p.status not in ('received','partial'): raise HTTPException(409,'فقط خرید دریافت‌شده قابل برگشت است')
 total=Decimal(0);seen=set()
 for ri in x.items:
  if ri.product_id in seen: raise HTTPException(400,'کالای تکراری در برگشت')
  seen.add(ri.product_id)
  it=s.scalar(select(PurchaseItem).where(PurchaseItem.purchase_id==p.id,PurchaseItem.product_id==ri.product_id).with_for_update())
  if not it: raise HTTPException(404,'کالا در این خرید نیست')
  if D(it.returned_qty)+D(ri.quantity)>D(it.received_qty): raise HTTPException(400,'مقدار برگشتی از مقدار خریداری‌شده بیشتر است')
  st=s.scalar(select(Stock).where(Stock.warehouse_id==p.warehouse_id,Stock.product_id==it.product_id).with_for_update())
  if not st or D(st.quantity)-D(st.reserved)<D(ri.quantity): raise HTTPException(400,'موجودی قابل فروش انبار برای برگشت کافی نیست')
  unit=line_unit_cost(it.quantity,D(it.quantity)*D(it.unit_cost),it.discount,it.landed)
  prod=s.get(Product,it.product_id,with_for_update=True);apply_return_cost(s,prod,ri.quantity,unit)   # قبل از کم‌کردن موجودی (وزن موجودی فعلی)
  st.quantity-=ri.quantity;it.returned_qty=D(it.returned_qty)+D(ri.quantity)
  if it.batch_no: consume_batches(s,cid,p.warehouse_id,it.product_id,ri.quantity,it.batch_no,strict=True)
  s.add(StockMove(company_id=cid,warehouse_id=p.warehouse_id,product_id=it.product_id,kind='purchase_return',quantity=ri.quantity,unit_cost=unit,reference=p.number,reason=(x.reason or 'برگشت از خرید')[:200],user_id=u.id))
  total+=(D(ri.quantity)*D(unit)).quantize(Q2)
 if total<=0: raise HTTPException(400,'مبلغ برگشت صفر است')
 e=post_entry(s,cid,u.id,f'برگشت از خرید {p.number}'+(f' — {x.reason}' if x.reason else ''),[{'code':AP,'debit':total,'supplier_id':p.supplier_id},{'code':INVT,'credit':total}],source=('purchase_return',p.id))
 audit(s,cid,u.id,'return','purchase',p.id,{'total':str(total),'items':[i.model_dump() for i in x.items]});s.commit();return {'purchase_id':p.id,'total':str(total),'entry':e.number}
