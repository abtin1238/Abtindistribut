"""صفحه‌بندی استاندارد لیست‌ها: ?limit=&offset= و هدر X-Total-Count (بدنه همان آرایه‌ی قبلی می‌ماند)"""
from __future__ import annotations
from fastapi import Response
from sqlalchemy import func,select

def set_total(response:Response,total:int,limit:int,offset:int):
 response.headers['X-Total-Count']=str(total);response.headers['X-Limit']=str(limit);response.headers['X-Offset']=str(offset)
def count_of(s,stmt): return s.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
def page_rows(s,stmt,response:Response,limit:int,offset:int):
 """stmt یک select با شرط‌ها؛ ترتیب پایدار با خود فراخواننده (مثلاً order_by(id))"""
 set_total(response,count_of(s,stmt),limit,offset)
 return s.scalars(stmt.limit(limit).offset(offset)).all()
