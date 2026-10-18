"""مرحله ۱۳ — نقشه و GPS: ثبت دسته‌ای موقعیت (آفلاین‌پذیر)، موقعیت زنده، تاریخچه‌ی حرکت، زمان حضور نزد مشتری.
حریم خصوصی: فقط داخل ساعت/روز کاری ذخیره می‌شود؛ مشاهده‌ی دیگران نیازمند gps.read + data.all؛ هر مشاهده‌ی مسیر دیگران audit می‌شود؛
نقاط پس از retention_days حذف می‌شوند."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.modules.gps import geofence as _gf
from app.modules.gps.schemas import GeofenceIn, GeofencePatch
from app.schemas import GpsBatchIn, TrackingSettingsIn
from .service import get_tracking as _s_get_tracking, put_tracking as _s_put_tracking, gps_config as _s_gps_config, post_points as _s_post_points, gps_users as _s_gps_users, gps_live as _s_gps_live, gps_track as _s_gps_track, gps_customers as _s_gps_customers, purge as _s_purge

router=APIRouter()

@router.get('/api/settings/tracking')
def get_tracking(ctx=Depends(current), s: Session=Depends(db)):
 return _s_get_tracking(ctx=ctx, s=s)

@router.put('/api/settings/tracking')
def put_tracking(x: TrackingSettingsIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_put_tracking(x=x, ctx=ctx, s=s)

@router.get('/api/gps/config')
def gps_config(ctx=Depends(current), s: Session=Depends(db)):
 return _s_gps_config(ctx=ctx, s=s)

@router.post('/api/gps/points')
def post_points(x: GpsBatchIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_post_points(x=x, ctx=ctx, s=s)

@router.get('/api/gps/users')
def gps_users(ctx=Depends(current), s: Session=Depends(db)):
 return _s_gps_users(ctx=ctx, s=s)

@router.get('/api/gps/live')
def gps_live(minutes: int=Query(15, ge=1, le=240), ctx=Depends(current), s: Session=Depends(db)):
 return _s_gps_live(minutes=minutes, ctx=ctx, s=s)

@router.get('/api/gps/track')
def gps_track(user_id: Optional[int]=None, day: Optional[str]=None, max_points: int=Query(2000, ge=50, le=10000), ctx=Depends(current), s: Session=Depends(db)):
 return _s_gps_track(user_id=user_id, day=day, max_points=max_points, ctx=ctx, s=s)

@router.get('/api/gps/customers')
def gps_customers(bbox: Optional[str]=None, region: str='', q: str='', limit: int=Query(5000, ge=1, le=20000), ctx=Depends(current), s: Session=Depends(db)):
 return _s_gps_customers(bbox=bbox, region=region, q=q, limit=limit, ctx=ctx, s=s)

@router.post('/api/gps/purge')
def purge(ctx=Depends(current), s: Session=Depends(db)):
 return _s_purge(ctx=ctx, s=s)

@router.get('/api/geofences')
def geofences(ctx=Depends(current), s: Session=Depends(db)):
 return _gf.geofences(ctx=ctx, s=s)

@router.post('/api/geofences')
def add_geofence(x: GeofenceIn, ctx=Depends(current), s: Session=Depends(db)):
 return _gf.add_geofence(x=x, ctx=ctx, s=s)

@router.patch('/api/geofences/{gid}')
def patch_geofence(gid: int, x: GeofencePatch, ctx=Depends(current), s: Session=Depends(db)):
 return _gf.patch_geofence(gid=gid, x=x, ctx=ctx, s=s)

@router.delete('/api/geofences/{gid}')
def delete_geofence(gid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _gf.delete_geofence(gid=gid, ctx=ctx, s=s)

@router.get('/api/geofences/events')
def geofence_events(user_id: Optional[int]=None, geofence_id: Optional[int]=None, day: Optional[str]=None, limit: int=Query(200, ge=1, le=2000), ctx=Depends(current), s: Session=Depends(db)):
 'رویدادهای ورود/خروج ناحیه (فقط کاربران در محدودهٔ دسترسی)'
 return _gf.geofence_events(user_id=user_id, geofence_id=geofence_id, day=day, limit=limit, ctx=ctx, s=s)
