from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,update
from sqlalchemy.exc import IntegrityError
from contextvars import ContextVar
from app.core.config import utcnow
from app.models import Audit,Sequence

def obj(x): return {k:v for k,v in x.__dict__.items() if not k.startswith('_')}
def list_json(s,model,cid,limit=500): return s.scalars(select(model).where(model.company_id==cid).limit(limit)).all()
REQ_CTX:ContextVar=ContextVar('req_ctx',default=None)  # {'ip':..., 'request_id':...} توسط middleware تنظیم می‌شود
def audit(s,cid,uid,action,entity,eid=None,detail=None):
 c=REQ_CTX.get() or {}
 s.add(Audit(company_id=cid,user_id=uid,action=action,entity=entity,entity_id=eid,detail=jsonable_encoder(detail or {}),ip=c.get('ip'),request_id=c.get('request_id')))
def next_seq(s,key):
 for _ in range(5):
  if s.execute(update(Sequence).where(Sequence.key==key).values(value=Sequence.value+1)).rowcount: return s.scalar(select(Sequence.value).where(Sequence.key==key))
  try:
   with s.begin_nested(): s.add(Sequence(key=key,value=1)); s.flush()
   return 1
  except IntegrityError: continue
 raise HTTPException(500,'خطا در شماره‌گذاری سند')
def num(prefix,cls,s): return f'{prefix}-{utcnow():%Y%m%d}-{next_seq(s,prefix+utcnow().strftime("%Y%m%d")):05d}'
def list_page(s,model,cid,response,limit=500,offset=0):
 """لیست صفحه‌بندی‌شده‌ی یک مدل شرکتی (ترتیب پایدار با id) + هدر X-Total-Count"""
 from app.core.paging import page_rows
 return page_rows(s,select(model).where(model.company_id==cid).order_by(model.id),response,limit,offset)
def same_company(s,model,id,cid):
 x=s.get(model,id)
 if not x or getattr(x,'company_id',None)!=cid: raise HTTPException(404,'رکورد یافت نشد')
 return x
Q2=Decimal('0.01')
def D(v): return Decimal(str(v if v is not None else 0))
ESC=chr(92)
def like_pat(q): return '%'+q.replace(ESC,ESC*2).replace('%',ESC+'%').replace('_',ESC+'_')+'%'
