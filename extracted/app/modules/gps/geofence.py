from __future__ import annotations
from datetime import timedelta
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import audit, obj, same_company
from app.models import Geofence, GeofenceEvent, User
from app.services.geo import evaluate_geofences, valid_point
from .schemas import GeofenceIn, GeofencePatch

def process_points(s: Session, cid: int, user_id: int, rows) -> int:
 """بعد از ذخیرهٔ نقاط GPS صدا زده می‌شود (بدون commit)؛ وضعیت قبلی از آخرین رویداد هر ناحیه برای همان کاربر می‌آید. نقاط قدیمی‌تر از آخرین رویداد کاربر نادیده گرفته می‌شوند تا ترتیب زمانی حفظ شود."""
 zones=[{'id':z.id,'lat':z.lat,'lng':z.lng,'radius_m':z.radius_m} for z in s.scalars(select(Geofence).where(Geofence.company_id==cid,Geofence.active==True)).all()]
 if not zones or not rows: return 0
 last={}
 for e in s.scalars(select(GeofenceEvent).where(GeofenceEvent.company_id==cid,GeofenceEvent.user_id==user_id,GeofenceEvent.geofence_id.in_([z['id'] for z in zones])).order_by(GeofenceEvent.at,GeofenceEvent.id)): last[e.geofence_id]=e
 inside={g for g,e in last.items() if e.kind=='enter'};floor=max((e.at for e in last.values()),default=None)
 pts=sorted(({'lat':p.lat,'lng':p.lng,'t':p.recorded_at} for p in rows if floor is None or p.recorded_at>floor),key=lambda p:p['t'])
 ev,_=evaluate_geofences(pts,zones,inside)
 for e in ev: s.add(GeofenceEvent(company_id=cid,user_id=user_id,geofence_id=e['geofence_id'],kind=e['kind'],at=e['t'],lat=e['lat'],lng=e['lng']))
 return len(ev)

def geofences(ctx, s: Session, include_inactive: bool=False):
 q=select(Geofence).where(Geofence.company_id==ctx[1])
 if not include_inactive: q=q.where(Geofence.active==True)
 return [obj(z) for z in s.scalars(q.order_by(Geofence.id)).all()]

def add_geofence(x: GeofenceIn, ctx, s: Session):
 u,cid,r=ctx
 if not valid_point(x.lat,x.lng): raise HTTPException(400,'مختصات نامعتبر است')
 if s.scalar(select(Geofence.id).where(Geofence.company_id==cid,Geofence.name==x.name)): raise HTTPException(409,'ناحیه‌ای با این نام وجود دارد')
 z=Geofence(company_id=cid,created_by=u.id,**x.model_dump());s.add(z);s.flush();audit(s,cid,u.id,'create','geofence',z.id,x.model_dump());s.commit();s.refresh(z);return obj(z)

def patch_geofence(gid: int, x: GeofencePatch, ctx, s: Session):
 u,cid,r=ctx;z=same_company(s,Geofence,gid,cid)
 for k,v in x.model_dump(exclude_unset=True).items():
  if v is not None: setattr(z,k,v)
 if not valid_point(z.lat,z.lng): raise HTTPException(400,'مختصات نامعتبر است')
 audit(s,cid,u.id,'update','geofence',z.id,x.model_dump(exclude_unset=True));s.commit();s.refresh(z);return obj(z)

def delete_geofence(gid: int, ctx, s: Session):
 u,cid,r=ctx;z=same_company(s,Geofence,gid,cid);z.active=False;audit(s,cid,u.id,'delete','geofence',z.id);s.commit();return {'id':z.id,'active':False}

def geofence_events(user_id: Optional[int], geofence_id: Optional[int], day: Optional[str], limit: int, ctx, s: Session):
 """رویدادهای ورود/خروج؛ کاربر بدون data.all فقط رویدادهای خودش را می‌بیند (همان قاعدهٔ مسیر GPS)."""
 from .service import _scope_users, tracking_cfg, day_range
 u,cid,r=ctx;users=_scope_users(ctx,s,user_id);q=select(GeofenceEvent).where(GeofenceEvent.company_id==cid)
 if users is not None: q=q.where(GeofenceEvent.user_id.in_(users))
 if geofence_id is not None: q=q.where(GeofenceEvent.geofence_id==geofence_id)
 if day: d,a,b=day_range(tracking_cfg(s,cid),day);q=q.where(GeofenceEvent.at>=a,GeofenceEvent.at<b)
 rows=s.scalars(q.order_by(GeofenceEvent.at.desc(),GeofenceEvent.id.desc()).limit(limit)).all()
 un={x.id:x.name for x in s.scalars(select(User).where(User.id.in_({e.user_id for e in rows} or {0}))).all()};zn={z.id:z.name for z in s.scalars(select(Geofence).where(Geofence.company_id==cid)).all()}
 if user_id is not None and user_id!=u.id: audit(s,cid,u.id,'view','geofence_events',user_id,{});s.commit()
 return [{**obj(e),'at':e.at.isoformat()+'Z','user':un.get(e.user_id,''),'geofence':zn.get(e.geofence_id,'')} for e in rows]
