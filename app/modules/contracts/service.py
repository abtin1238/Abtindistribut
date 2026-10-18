from __future__ import annotations
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import audit, num, same_company, obj
from app.models import Contract, Customer, Supplier
from .schemas import ContractIn, ContractPatch
from app.core.config import utcnow

STATUSES=('draft','active','expired','cancelled')

def _check(s,cid,x):
 if x.customer_id and x.supplier_id: raise HTTPException(400,'قرارداد فقط با یک طرف (مشتری یا تأمین‌کننده) ثبت می‌شود')
 if x.customer_id: same_company(s,Customer,x.customer_id,cid)
 if x.supplier_id: same_company(s,Supplier,x.supplier_id,cid)
 if x.start_date and x.end_date and x.end_date<x.start_date: raise HTTPException(400,'تاریخ پایان قبل از شروع است')

def _view(s,c):
 d=obj(c);d['party']=(s.get(Customer,c.customer_id).name if c.customer_id else s.get(Supplier,c.supplier_id).name if c.supplier_id else '')
 if c.status=='active' and c.end_date and c.end_date<utcnow().date(): d['status']='expired'   # انقضای خودکار در نمایش؛ بدون تغییر دادهٔ ذخیره‌شده
 return d

def contracts(status: Optional[str], customer_id: Optional[int], supplier_id: Optional[int], ctx, s: Session):
 q=select(Contract).where(Contract.company_id==ctx[1])
 if status: q=q.where(Contract.status==status)
 if customer_id: q=q.where(Contract.customer_id==customer_id)
 if supplier_id: q=q.where(Contract.supplier_id==supplier_id)
 return [_view(s,c) for c in s.scalars(q.order_by(Contract.id.desc()).limit(500))]

def contract_create(x: ContractIn, ctx, s: Session):
 u,cid,r=ctx;_check(s,cid,x)
 c=Contract(company_id=cid,number=num('CT',Contract,s),title=x.title.strip(),customer_id=x.customer_id,supplier_id=x.supplier_id,start_date=x.start_date,end_date=x.end_date,amount=x.amount,note=x.note,created_by=u.id);s.add(c);s.flush()
 audit(s,cid,u.id,'create','contract',c.id,{'number':c.number});s.commit();return _view(s,c)

def contract_get(cid_: int, ctx, s: Session):
 return _view(s, same_company(s, Contract, cid_, ctx[1]))

def contract_patch(cid_: int, x: ContractPatch, ctx, s: Session):
 u,cid,r=ctx;c=same_company(s,Contract,cid_,cid);d=x.model_dump(exclude_unset=True)
 if 'status' in d and d['status'] not in STATUSES: raise HTTPException(400,'وضعیت نامعتبر است')
 if c.status=='cancelled' and d.get('status') not in (None,'cancelled'): raise HTTPException(409,'قرارداد لغوشده قابل فعال‌سازی مجدد نیست')
 for k,v in d.items():
  if v is None and k in ('title','amount','status','note'): continue
  setattr(c,k,v)
 if c.start_date and c.end_date and c.end_date<c.start_date: raise HTTPException(400,'تاریخ پایان قبل از شروع است')
 audit(s,cid,u.id,'update','contract',c.id,d);s.commit();return _view(s,c)
