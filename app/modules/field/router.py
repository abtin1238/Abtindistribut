from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import PlanIn, VisitFinishIn, VisitIn, VisitRadiusIn
from .service import get_visit_settings as _s_get_visit_settings, put_visit_settings as _s_put_visit_settings, start_visit as _s_start_visit, finish_visit as _s_finish_visit, visit_photo as _s_visit_photo, today_visits as _s_today_visits, list_visits as _s_list_visits, visit_plans as _s_visit_plans, create_plan as _s_create_plan, today_plan as _s_today_plan, suggest_plan as _s_suggest_plan, plan_items as _s_plan_items

router=APIRouter()

@router.get('/api/settings/visit')
def get_visit_settings(ctx=Depends(current), s: Session=Depends(db)):
 return _s_get_visit_settings(ctx=ctx, s=s)

@router.put('/api/settings/visit')
def put_visit_settings(x: VisitRadiusIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_put_visit_settings(x=x, ctx=ctx, s=s)

@router.post('/api/visits')
def start_visit(x: VisitIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_start_visit(x=x, ctx=ctx, s=s)

@router.post('/api/visits/{vid}/finish')
def finish_visit(vid: int, ctx=Depends(current), s: Session=Depends(db), x: Optional[VisitFinishIn]=None):
 return _s_finish_visit(vid=vid, ctx=ctx, s=s, x=x)

@router.post('/api/visits/{vid}/photo')
async def visit_photo(vid: int, file: UploadFile=File(...), ctx=Depends(current), s: Session=Depends(db)):
 return await _s_visit_photo(vid=vid, file=file, ctx=ctx, s=s)

@router.get('/api/visits/today')
def today_visits(day: Optional[date]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_today_visits(day=day, ctx=ctx, s=s)

@router.get('/api/visits')
def list_visits(start: Optional[date]=None, end: Optional[date]=None, user_id: Optional[int]=None, customer_id: Optional[int]=None, gps_status: Optional[str]=None, limit: int=Query(200, ge=1, le=500), ctx=Depends(current), s: Session=Depends(db)):
 return _s_list_visits(start=start, end=end, user_id=user_id, customer_id=customer_id, gps_status=gps_status, limit=limit, ctx=ctx, s=s)

@router.get('/api/visit-plans')
def visit_plans(ctx=Depends(current), s: Session=Depends(db)):
 return _s_visit_plans(ctx=ctx, s=s)

@router.post('/api/visit-plans')
def create_plan(x: PlanIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_plan(x=x, ctx=ctx, s=s)

@router.get('/api/visit-plans/today')
def today_plan(day: Optional[date]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_today_plan(day=day, ctx=ctx, s=s)

@router.get('/api/visit-plans/suggest')
def suggest_plan(region: str='', day: Optional[date]=None, lat: Optional[float]=Query(None, ge=-90, le=90), lng: Optional[float]=Query(None, ge=-180, le=180), limit: int=Query(20, ge=1, le=100), ctx=Depends(current), s: Session=Depends(db)):
 return _s_suggest_plan(region=region, day=day, lat=lat, lng=lng, limit=limit, ctx=ctx, s=s)

@router.get('/api/visit-plans/{pid}/items')
def plan_items(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_plan_items(pid=pid, ctx=ctx, s=s)
