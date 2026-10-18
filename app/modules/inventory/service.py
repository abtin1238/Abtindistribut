from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import D, audit, list_json, num, obj, same_company
from app.core.config import utcnow
from app.core.security import wh_check, wh_scope
from app.models import StockTransferBatch, StockTransferItem, Product, Stock, StockMove, StockTransfer, Warehouse
from app.services.accounting import post_stock_adjust
from app.services.units import to_base_qty
from app.services.stock_batches import add_batch, batched_qty, consume_batches
from .schemas import WarehouseIn, StockIn, TransferIn, TransferItemIn

def warehouses(ctx, s: Session):
 sc=wh_scope(s,ctx);return [obj(x) for x in list_json(s,Warehouse,ctx[1]) if sc is None or x.id in sc]

def add_warehouse(x: WarehouseIn, ctx, s: Session):
 u,cid,r=ctx
 if x.company_id!=cid: raise HTTPException(403,'شرکت نامعتبر')
 q=Warehouse(**x.model_dump());s.add(q);audit(s,cid,u.id,'create','warehouse');s.commit();s.refresh(q);return obj(q)

def stock(ctx, s: Session):
 cid=ctx[1];sc=wh_scope(s,ctx); q=[x for x in s.execute(select(Stock,Product,Warehouse).join(Product,Product.id==Stock.product_id).join(Warehouse,Warehouse.id==Stock.warehouse_id).where(Product.company_id==cid,Warehouse.company_id==cid)) if sc is None or x[0].warehouse_id in sc]; return [{'id':st.id,'product_id':st.product_id,'product':p.name,'sku':p.sku,'warehouse_id':st.warehouse_id,'warehouse':w.name,'quantity':st.quantity,'reserved':st.reserved,'available':st.quantity-st.reserved,'location':st.location} for st,p,w in q]

def adjust_stock(x: StockIn, ctx, s: Session):
 u,cid,r=ctx; w=s.get(Warehouse,x.warehouse_id); p=s.get(Product,x.product_id)
 if not w or w.company_id!=cid or not p or p.company_id!=cid: raise HTTPException(404,'انبار یا کالا یافت نشد')
 wh_check(s,ctx,w.id)
 if x.kind not in ('in','out'): raise HTTPException(400,'نوع تعدیل باید in یا out باشد')
 if x.quantity<=0: raise HTTPException(400,'مقدار باید مثبت باشد')
 reason=(x.reason or '').strip() or (x.reference if x.reference not in ('','manual') else '')
 if x.kind=='out' and not reason: raise HTTPException(400,'دلیل خروج از انبار الزامی است')
 reason=reason or 'ورود دستی'
 st=s.scalar(select(Stock).where(Stock.warehouse_id==w.id,Stock.product_id==p.id).with_for_update()) or Stock(warehouse_id=w.id,product_id=p.id,quantity=0,reserved=0);s.add(st);delta=x.quantity if x.kind=='in' else -x.quantity
 if st.quantity-st.reserved+delta<0: raise HTTPException(400,'موجودی قابل فروش کافی نیست')
 if x.kind=='in':
  if x.batch_no.strip() or p.track_batch: add_batch(s,cid,w.id,p.id,x.quantity,x.batch_no,x.expiry_date)
 elif x.batch_no.strip() or p.track_batch:
  unbatched=D(st.quantity)-batched_qty(s,w.id,p.id)
  if consume_batches(s,cid,w.id,p.id,x.quantity,x.batch_no,strict=True)>max(unbatched,0): raise HTTPException(400,'موجودی بچ‌ها برای این خروج کافی نیست')
 st.quantity+=delta;s.add(StockMove(company_id=cid,warehouse_id=w.id,product_id=p.id,kind=x.kind,quantity=x.quantity,unit_cost=p.avg_cost if p.avg_cost else None,reference=x.reference,reason=reason[:200],user_id=u.id));post_stock_adjust(s,cid,u.id,p,delta,x.reference);audit(s,cid,u.id,'stock_adjust','stock',st.id,x.model_dump(mode='json'));s.commit();return obj(st)

def _items(s: Session, t: StockTransfer):
 """اقلام برگهٔ انتقال؛ برای انتقال‌های قدیمی (بدون ردیف) از سرتیتر خوانده می‌شود."""
 rows=s.scalars(select(StockTransferItem).where(StockTransferItem.transfer_id==t.id).order_by(StockTransferItem.id)).all()
 return [(r.product_id,D(r.quantity)) for r in rows] or [(t.product_id,D(t.quantity))]

def _batches_of(s: Session, t: StockTransfer, pid: int):
 """بچ‌های در راهِ یک قلم (ردیف قدیمی با product_id خالی متعلق به کالای سرتیتر است)"""
 return [tb for tb in s.scalars(select(StockTransferBatch).where(StockTransferBatch.transfer_id==t.id)) if (tb.product_id or t.product_id)==pid]

def create_transfer(x: TransferIn, ctx, s: Session):
 u,cid,r=ctx
 if x.from_warehouse_id==x.to_warehouse_id: raise HTTPException(400,'انبار مبدأ و مقصد نباید یکسان باشند')
 a=s.get(Warehouse,x.from_warehouse_id);b=s.get(Warehouse,x.to_warehouse_id)
 if not a or a.company_id!=cid or not b or b.company_id!=cid: raise HTTPException(404,'انبار یا کالا یافت نشد')
 merged={}
 for it in x.items: merged[it.product_id]=merged.get(it.product_id,Decimal(0))+to_base_qty(s,cid,it.product_id,it.unit,it.quantity)   # به واحد پایه
 x.items=[TransferItemIn(product_id=k,quantity=v) for k,v in merged.items()]
 prods={}
 for it in x.items:
  p=s.get(Product,it.product_id)
  if not p or p.company_id!=cid: raise HTTPException(404,'انبار یا کالا یافت نشد')
  prods[p.id]=p
 sts={}
 for it in sorted(x.items,key=lambda i:i.product_id):   # ترتیب ثابت قفل‌ها = بدون بن‌بست
  st=s.scalar(select(Stock).where(Stock.warehouse_id==a.id,Stock.product_id==it.product_id).with_for_update())
  if not st or D(st.quantity)-D(st.reserved)<D(it.quantity): raise HTTPException(400,f'موجودی قابل انتقال «{prods[it.product_id].name}» کافی نیست')
  sts[it.product_id]=st
 first=x.items[0];total=sum((D(i.quantity) for i in x.items),Decimal(0))
 t=StockTransfer(company_id=cid,number=num('TRF',StockTransfer,s),from_warehouse_id=a.id,to_warehouse_id=b.id,product_id=first.product_id,quantity=total,note=x.note,created_by=u.id);s.add(t);s.flush()
 for it in x.items:
  q=D(it.quantity);sts[it.product_id].quantity=D(sts[it.product_id].quantity)-q;alloc=[]
  consume_batches(s,cid,a.id,it.product_id,q,out=alloc)
  s.add(StockTransferItem(transfer_id=t.id,product_id=it.product_id,quantity=q))
  s.add(StockMove(company_id=cid,warehouse_id=a.id,product_id=it.product_id,kind='transfer_out',quantity=q,reference=t.number,reason=(x.note or 'انتقال بین انبارها')[:200],user_id=u.id))
  for bn,ex,bq in alloc: s.add(StockTransferBatch(transfer_id=t.id,product_id=it.product_id,batch_no=bn,expiry_date=ex,quantity=bq))
 audit(s,cid,u.id,'create','stock_transfer',t.id,x.model_dump(mode='json'));s.commit();return _with_items(s,t)

def _move_in(s: Session, t: StockTransfer, wid: int, kind: str, reason: str, uid: int):
 """ورود اقلام برگه به انبار wid (دریافت در مقصد یا برگشت به مبدأ در لغو)"""
 for pid,q in sorted(_items(s,t)):
  st=s.scalar(select(Stock).where(Stock.warehouse_id==wid,Stock.product_id==pid).with_for_update()) or Stock(warehouse_id=wid,product_id=pid,quantity=0,reserved=0)
  s.add(st);st.quantity=D(st.quantity)+q
  s.add(StockMove(company_id=t.company_id,warehouse_id=wid,product_id=pid,kind=kind,quantity=q,reference=t.number,reason=reason,user_id=uid))
  for tb in _batches_of(s,t,pid): add_batch(s,t.company_id,wid,pid,tb.quantity,tb.batch_no,tb.expiry_date)

def receive_transfer(tid: int, ctx, s: Session):
 u,cid,r=ctx;t=same_company(s,StockTransfer,tid,cid)
 if t.status!='in_transit': raise HTTPException(409,'این انتقال قابل دریافت نیست')
 _move_in(s,t,t.to_warehouse_id,'transfer_in','دریافت انتقال',u.id)
 t.status='received';t.received_by=u.id;t.received_at=utcnow()
 audit(s,cid,u.id,'receive','stock_transfer',t.id);s.commit();return _with_items(s,t)

def cancel_transfer(tid: int, ctx, s: Session):
 u,cid,r=ctx;t=same_company(s,StockTransfer,tid,cid)
 if t.status!='in_transit': raise HTTPException(409,'این انتقال قابل لغو نیست')
 _move_in(s,t,t.from_warehouse_id,'transfer_cancel','لغو انتقال',u.id)
 t.status='cancelled'
 audit(s,cid,u.id,'cancel','stock_transfer',t.id);s.commit();return _with_items(s,t)

def _with_items(s: Session, t: StockTransfer):
 names={p.id:p.name for p in s.scalars(select(Product).where(Product.id.in_([pid for pid,_ in _items(s,t)])))}
 return {**obj(t),'items':[{'product_id':pid,'product':names.get(pid,''),'quantity':q} for pid,q in _items(s,t)]}

def list_transfers(ctx, s: Session):
 ts=list(s.scalars(select(StockTransfer).where(StockTransfer.company_id == ctx[1]).order_by(StockTransfer.id.desc()).limit(500)))
 if not ts: return []
 by={}
 for r in s.scalars(select(StockTransferItem).where(StockTransferItem.transfer_id.in_([t.id for t in ts])).order_by(StockTransferItem.id)): by.setdefault(r.transfer_id,[]).append((r.product_id,D(r.quantity)))
 names={p.id:p.name for p in s.scalars(select(Product).where(Product.company_id==ctx[1]))}
 out=[]
 for t in ts:
  its=by.get(t.id) or [(t.product_id,D(t.quantity))]
  out.append({**obj(t),'items':[{'product_id':pid,'product':names.get(pid,''),'quantity':q} for pid,q in its],'items_count':len(its),'products':'، '.join(names.get(pid,'') for pid,_ in its)})
 return out

def report_stock(warehouse_id: Optional[int], ctx, s: Session):
 cid=ctx[1];prods={p.id:p for p in s.scalars(select(Product).where(Product.company_id==cid))};mins={i:p.min_stock for i,p in prods.items()}
 rows=stock(ctx,s)
 if warehouse_id is not None: rows=[x for x in rows if x['warehouse_id']==warehouse_id]
 for x in rows:
  m=mins.get(x['product_id']) or Decimal(0);x['min_stock']=m;x['shortage']=max(Decimal(0),m-x['available']);mx=D(getattr(prods.get(x['product_id']),'max_stock',0));x['max_stock']=mx;x['over_max']=mx>0 and x['quantity']>mx
 low=[x for x in rows if x['available']<=0 or (x['min_stock']>0 and x['available']<=x['min_stock'])]
 return {'items':rows,'low_stock':low,'over_stock':[x for x in rows if x['over_max']]}
