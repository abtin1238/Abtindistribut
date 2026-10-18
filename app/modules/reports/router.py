from __future__ import annotations
from datetime import date
from typing import Literal, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .schemas import JobIn
from .service import profit_breakdown as _s_profit_breakdown, profit_breakdown_xlsx as _s_profit_breakdown_xlsx, catalog as _s_catalog, run as _s_run, sales_drill as _s_sales_drill, export as _s_export, job_create as _s_job_create, job_list as _s_job_list, job_get as _s_job_get, job_download as _s_job_download

router=APIRouter()

@router.get('/api/reports/profit-loss/breakdown')
def profit_breakdown(by: str=Query('product'), start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_profit_breakdown(by=by, start=start, end=end, ctx=ctx, s=s)

@router.get('/api/reports/profit-loss/breakdown.xlsx')
def profit_breakdown_xlsx(by: str=Query('product'), start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_profit_breakdown_xlsx(by=by, start=start, end=end, ctx=ctx, s=s)

@router.get('/api/reports/catalog')
def catalog(ctx=Depends(current), s: Session=Depends(db)):
 return _s_catalog(ctx=ctx, s=s)

@router.get('/api/reports/run/{name}')
def run(name: str, request: Request, ctx=Depends(current), s: Session=Depends(db)):
 return _s_run(name=name, request=request, ctx=ctx, s=s)

@router.get('/api/reports/sales/detail')
def sales_drill(request: Request, ctx=Depends(current), s: Session=Depends(db)):
 return _s_sales_drill(request=request, ctx=ctx, s=s)

@router.get('/api/reports/run/{name}/export')
def export(name: str, request: Request, format: Literal['xlsx', 'pdf']=Query('xlsx'), ctx=Depends(current), s: Session=Depends(db)):
 'خروجی هم\u200cزمان برای گزارش\u200cهای کوچک؛ گزارش بزرگ باید با /api/reports/jobs در صف ساخته شود'
 return _s_export(name=name, request=request, format=format, ctx=ctx, s=s)

@router.post('/api/reports/jobs')
def job_create(x: JobIn, bg: BackgroundTasks, ctx=Depends(current), s: Session=Depends(db)):
 return _s_job_create(x=x, bg=bg, ctx=ctx, s=s)

@router.get('/api/reports/jobs')
def job_list(ctx=Depends(current), s: Session=Depends(db)):
 return _s_job_list(ctx=ctx, s=s)

@router.get('/api/reports/jobs/{jid}')
def job_get(jid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_job_get(jid=jid, ctx=ctx, s=s)

@router.get('/api/reports/jobs/{jid}/download')
def job_download(jid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_job_download(jid=jid, ctx=ctx, s=s)
