from __future__ import annotations
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.common import audit, obj
from app.core.security import has_all
from app.models import SavedFilter
from app.services.search import SPEC, advanced, allowed, global_search, schema, validate_query
from .schemas import AdvIn, SavedIn

def search_schema(ctx):
 return schema(ctx[2])

def search_global(q: str, types: Optional[str], limit: int, ctx, s: Session):
 ts={x for x in (types or '').split(',') if x} or None
 if ts and not ts<=set(SPEC): raise HTTPException(400,'نوع جستجو نامعتبر است')
 return {'q':q,'results':global_search(s,ctx,q,ts,limit)}

def search_advanced(x: AdvIn, ctx, s: Session):
 return advanced(s,ctx,x.entity,{'q':x.q,'filters':x.filters,'sort':x.sort,'order':x.order},x.page,x.page_size)

def saved_list(entity: Optional[str], ctx, s: Session):
 u,cid,r=ctx;q=select(SavedFilter).where(SavedFilter.company_id==cid,or_(SavedFilter.user_id==u.id,SavedFilter.shared==True),SavedFilter.entity.in_(list(allowed(r))))
 if entity: q=q.where(SavedFilter.entity==entity)
 return [{**obj(x),'mine':x.user_id==u.id} for x in s.scalars(q.order_by(SavedFilter.entity,SavedFilter.name))]

def saved_save(x: SavedIn, ctx, s: Session):
 u,cid,r=ctx;qq=validate_query(r,x.entity,x.query)   # فقط پرسمان معتبر و مجاز ذخیره می‌شود
 row=s.scalar(select(SavedFilter).where(SavedFilter.company_id==cid,SavedFilter.user_id==u.id,SavedFilter.entity==x.entity,SavedFilter.name==x.name.strip()))
 if row: row.query=qq;row.shared=x.shared
 else:
  row=SavedFilter(company_id=cid,user_id=u.id,entity=x.entity,name=x.name.strip(),query=qq,shared=x.shared);s.add(row)
 try: s.flush();audit(s,cid,u.id,'save','saved_filter',row.id,{'entity':x.entity,'name':row.name});s.commit()
 except IntegrityError: s.rollback();raise HTTPException(409,'فیلتری با این نام وجود دارد')
 return obj(row)

def saved_delete(fid: int, ctx, s: Session):
 u,cid,r=ctx;row=s.get(SavedFilter,fid)
 if not row or row.company_id!=cid or (row.user_id!=u.id and not (has_all(r) and row.shared)): raise HTTPException(404,'فیلتر یافت نشد')
 s.delete(row);audit(s,cid,u.id,'delete','saved_filter',fid);s.commit();return {'ok':True}

def search_status(ctx, s: Session):
 """وضعیت ایندکس pg_trgm (فقط مدیر). اگر ناقص باشد، دستور SQL لازم برای DBA برگردانده می‌شود؛ هر بار راه‌اندازی/مایگریشن دوباره تلاش می‌کند."""
 if not has_all(ctx[2]): raise HTTPException(403,'دسترسی کافی نیست')
 from app.core import pgtrgm
 return pgtrgm.status(s.connection())
