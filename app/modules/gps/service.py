from __future__ import annotations
import json
from datetime import timedelta, date, datetime, timezone
from fastapi import HTTPException
from sqlalchemy import func, select, delete
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import audit, like_pat
from app.core.config import utcnow
from app.core.security import has_all, need, has_perm
from app.models import Customer, Delivery, GpsPoint, Membership, Order, Role, Setting, User, Visit
from app.modules.field import visit_radius
from app.services.geo import detect_stays, thin_points, track_distance_m, MAX_ACCURACY_M, valid_point
from sqlalchemy.exc import IntegrityError
from .geofence import process_points
from .schemas import GpsBatchIn, TrackingSettingsIn

DEFAULTS=TrackingSettingsIn().model_dump()

MAX_TRACK_ROWS=20000;MAX_AGE_DAYS=7



def iso(d): return None if d is None else d.isoformat()+'Z'

def naive_utc(d):
 if d is None: return None
 return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d

def tracking_cfg(s,cid)->dict:
 v=s.scalar(select(Setting.value).where(Setting.company_id==cid,Setting.key=='tracking'))
 try: cur=json.loads(v) if v else {}
 except ValueError: cur={}
 return {**DEFAULTS,**{k:x for k,x in cur.items() if k in DEFAULTS}}

def local_dt(cfg,t): return t+timedelta(minutes=cfg['tz_offset_min'])

def in_work_hours(cfg,t)->bool:
 l=local_dt(cfg,t)
 return l.weekday() in cfg['work_days'] and cfg['work_start']<=l.strftime('%H:%M')<=cfg['work_end']

def day_range(cfg,day:Optional[str]):
 try: d=date.fromisoformat(day) if day else local_dt(cfg,utcnow()).date()
 except ValueError as e: raise HTTPException(400,'تاریخ نامعتبر است (YYYY-MM-DD)') from e
 start=datetime(d.year,d.month,d.day)-timedelta(minutes=cfg['tz_offset_min']);return d,start,start+timedelta(days=1)

def ingest_points(x:GpsBatchIn,ctx,s)->dict:
 u,cid,r=ctx;cfg=tracking_cfg(s,cid);now=utcnow();res={'received':len(x.points),'stored':0,'duplicate':0,'outside_hours':0,'invalid':0,'tracking_disabled':0}
 if not cfg['enabled']: res['tracking_disabled']=len(x.points);return res
 ids=[p.client_id for p in x.points if p.client_id]
 have=set(s.scalars(select(GpsPoint.client_id).where(GpsPoint.company_id==cid,GpsPoint.user_id==u.id,GpsPoint.client_id.in_(ids)))) if ids else set()
 rows=[]
 for p in x.points:
  t=naive_utc(p.recorded_at) or now
  if t>now+timedelta(minutes=5) or t<now-timedelta(days=MAX_AGE_DAYS) or not valid_point(p.lat,p.lng) or (p.accuracy_m or 0)>MAX_ACCURACY_M: res['invalid']+=1;continue
  if p.client_id and p.client_id in have: res['duplicate']+=1;continue
  if not in_work_hours(cfg,t): res['outside_hours']+=1;continue
  if p.client_id: have.add(p.client_id)
  rows.append(GpsPoint(company_id=cid,user_id=u.id,client_id=p.client_id,lat=p.lat,lng=p.lng,accuracy_m=p.accuracy_m,speed_mps=p.speed_mps,recorded_at=t,received_at=now))
 try: s.add_all(rows);process_points(s,cid,u.id,rows);s.commit();res['stored']=len(rows)
 except IntegrityError:  # درخواست موازی همان client_id را زودتر ثبت کرد؛ تک‌تک با savepoint
  s.rollback()
  kept=[]
  for g in rows:
   try:
    with s.begin_nested(): s.add(GpsPoint(company_id=g.company_id,user_id=g.user_id,client_id=g.client_id,lat=g.lat,lng=g.lng,accuracy_m=g.accuracy_m,speed_mps=g.speed_mps,recorded_at=g.recorded_at,received_at=g.received_at));s.flush()
    res['stored']+=1;kept.append(g)
   except IntegrityError: res['duplicate']+=1
  process_points(s,cid,u.id,kept);s.commit()
 return res

def _kind(role)->str:
 if has_perm(role,'visit.write'): return 'visitor'
 if has_perm(role,'delivery.update'): return 'driver'
 return 'other'

def _scope_users(ctx,s,user_id:Optional[int]):
 """None = همه‌ی اعضای شرکت؛ وگرنه {id}. بدون data.all فقط خود کاربر."""
 u,cid,r=ctx
 if user_id is not None and user_id!=u.id and not has_all(r): raise HTTPException(403,'فقط مسیر خودتان قابل مشاهده است')
 if not has_all(r): return {u.id}
 if user_id is None: return None
 if not s.scalar(select(Membership.id).where(Membership.company_id==cid,Membership.user_id==user_id)): raise HTTPException(404,'کاربر یافت نشد')
 return {user_id}

def purge_gps(s,cid=None)->int:
 n=0
 for c in ([cid] if cid else list(s.scalars(select(Setting.company_id).where(Setting.key=='tracking').distinct()))):
  days=tracking_cfg(s,c)['retention_days'];n+=s.execute(delete(GpsPoint).where(GpsPoint.company_id==c,GpsPoint.recorded_at<utcnow()-timedelta(days=days))).rowcount or 0
 if not cid:  # شرکت‌های بدون تنظیم صریح با مقدار پیش‌فرض
  n+=s.execute(delete(GpsPoint).where(GpsPoint.company_id.notin_(select(Setting.company_id).where(Setting.key=='tracking')),GpsPoint.recorded_at<utcnow()-timedelta(days=DEFAULTS['retention_days']))).rowcount or 0
 s.commit();return n

def get_tracking(ctx, s: Session):
 return tracking_cfg(s, ctx[1])

def put_tracking(x: TrackingSettingsIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write')
 if x.work_start>=x.work_end: raise HTTPException(400,'ساعت شروع باید قبل از پایان باشد')
 if any(d<0 or d>6 for d in x.work_days) or len(set(x.work_days))!=len(x.work_days): raise HTTPException(400,'روزهای کاری نامعتبر است (۰=دوشنبه … ۶=یکشنبه)')
 v=json.dumps(x.model_dump());row=s.scalar(select(Setting).where(Setting.company_id==cid,Setting.key=='tracking'))
 if row: row.value=v
 else: s.add(Setting(company_id=cid,key='tracking',value=v))
 audit(s,cid,u.id,'update','tracking_settings',None,x.model_dump());s.commit();return x.model_dump()

def gps_config(ctx, s: Session):
 cfg=tracking_cfg(s,ctx[1]);return {**cfg,'active_now':cfg['enabled'] and in_work_hours(cfg,utcnow()),'server_time':iso(utcnow())}

def post_points(x: GpsBatchIn, ctx, s: Session):
 return ingest_points(x, ctx, s)

def gps_users(ctx, s: Session):
 u,cid,r=ctx;q=select(User,Role).join(Role,Role.id==User.role_id).join(Membership,Membership.user_id==User.id).where(Membership.company_id==cid,User.active==True)
 if not has_all(r): q=q.where(User.id==u.id)
 return [{'id':x.id,'name':x.name,'role':ro.name,'kind':_kind(ro)} for x,ro in s.execute(q.order_by(User.name)).all()]

def gps_live(minutes: int, ctx, s: Session):
 u,cid,r=ctx;cfg=tracking_cfg(s,cid);now=utcnow()
 if not cfg['enabled'] or not in_work_hours(cfg,now): return {'active':False,'users':[]}
 users=_scope_users(ctx,s,None);since=now-timedelta(minutes=minutes)
 q=select(GpsPoint).where(GpsPoint.company_id==cid,GpsPoint.recorded_at>=since).order_by(GpsPoint.recorded_at.desc(),GpsPoint.id.desc())
 if users is not None: q=q.where(GpsPoint.user_id.in_(users))
 last={}
 for p in s.scalars(q.limit(20000)):
  last.setdefault(p.user_id,p)
 names={x.id:(x,ro) for x,ro in s.execute(select(User,Role).join(Role,Role.id==User.role_id).where(User.id.in_(list(last) or [0]))).all()}
 out=[{'user_id':uid,'name':names[uid][0].name,'role':names[uid][1].name,'kind':_kind(names[uid][1]),'lat':p.lat,'lng':p.lng,'accuracy_m':p.accuracy_m,'speed_mps':p.speed_mps,'recorded_at':iso(p.recorded_at),'age_s':int((now-p.recorded_at).total_seconds())} for uid,p in last.items() if uid in names]
 return {'active':True,'users':sorted(out,key=lambda x:x['age_s'])}

def gps_track(user_id: Optional[int], day: Optional[str], max_points: int, ctx, s: Session):
 u,cid,r=ctx;cfg=tracking_cfg(s,cid);target=user_id if user_id is not None else u.id;_scope_users(ctx,s,target)
 d,a,b=day_range(cfg,day);tu=s.get(User,target)
 if not tu: raise HTTPException(404,'کاربر یافت نشد')
 if target!=u.id: audit(s,cid,u.id,'view','gps_track',target,{'day':d.isoformat()});s.commit()
 rows=s.scalars(select(GpsPoint).where(GpsPoint.company_id==cid,GpsPoint.user_id==target,GpsPoint.recorded_at>=a,GpsPoint.recorded_at<b).order_by(GpsPoint.recorded_at,GpsPoint.id).limit(MAX_TRACK_ROWS)).all()
 pts=[{'lat':p.lat,'lng':p.lng,'t':p.recorded_at,'acc':p.accuracy_m} for p in rows]
 stays=[];radius=visit_radius(s,cid)
 if pts:
  pad=0.02;la=[p['lat'] for p in pts];ln=[p['lng'] for p in pts]
  cs=s.scalars(select(Customer).where(Customer.company_id==cid,Customer.lat!=None,Customer.lng!=None,Customer.lat.between(min(la)-pad,max(la)+pad),Customer.lng.between(min(ln)-pad,max(ln)+pad)).limit(5000)).all()
  stays=detect_stays(pts,[{'id':c.id,'name':c.name,'lat':c.lat,'lng':c.lng} for c in cs],radius)
 vs=s.execute(select(Visit,Customer.name).join(Customer,Customer.id==Visit.customer_id).where(Visit.company_id==cid,Visit.user_id==target,Visit.started_at>=a,Visit.started_at<b).order_by(Visit.started_at)).all()
 def overlap(st,v):
  ve=v.ended_at or max(v.started_at,st['exit']);return st['place_id']==v.customer_id and st['enter']<=ve+timedelta(minutes=10) and st['exit']>=v.started_at-timedelta(minutes=10)
 visits=[]
 for v,cn in vs:
  m=next((st for st in stays if overlap(st,v)),None)
  visits.append({'id':v.id,'customer_id':v.customer_id,'customer_name':cn,'started_at':iso(v.started_at),'ended_at':iso(v.ended_at),'result':v.result,'gps_status':v.gps_status,'lat':v.lat,'lng':v.lng,'gps_presence':(None if not pts else m is not None),'presence_minutes':m['minutes'] if m else None})
 ds=s.execute(select(Delivery,Order.number,Customer.name).join(Order,Order.id==Delivery.order_id).join(Customer,Customer.id==Order.customer_id).where(Delivery.company_id==cid,Delivery.driver_id==target,Delivery.delivered_at!=None,Delivery.delivered_at>=a,Delivery.delivered_at<b)).all()
 deliveries=[{'id':x.id,'order_number':n,'customer_name':cn,'status':x.status,'at':iso(x.delivered_at),'lat':x.lat,'lng':x.lng,'gps_status':x.gps_status} for x,n,cn in ds]
 shown=thin_points(pts,max_points)
 return {'user':{'id':tu.id,'name':tu.name},'day':d.isoformat(),'tz_offset_min':cfg['tz_offset_min'],'radius_m':radius,'point_count':len(pts),'distance_km':round(track_distance_m(pts)/1000,2),'first_at':iso(pts[0]['t']) if pts else None,'last_at':iso(pts[-1]['t']) if pts else None,
  'points':[{'lat':p['lat'],'lng':p['lng'],'t':iso(p['t']),'acc':p['acc']} for p in shown],
  'stays':[{'customer_id':st['place_id'],'customer_name':st['name'],'enter':iso(st['enter']),'exit':iso(st['exit']),'minutes':st['minutes'],'min_distance_m':st['min_distance_m']} for st in stays],'visits':visits,'deliveries':deliveries}

def gps_customers(bbox: Optional[str], region: str, q: str, limit: int, ctx, s: Session):
 cid=ctx[1];w=[Customer.company_id==cid,Customer.active==True]
 if region: w.append(Customer.region==region)
 if q: w.append(Customer.name.like(like_pat(q),escape=chr(92)))
 total_no=s.scalar(select(func.count(Customer.id)).where(*w,(Customer.lat==None)|(Customer.lng==None))) or 0
 w+= [Customer.lat!=None,Customer.lng!=None]
 if bbox:
  try: x1,y1,x2,y2=[float(v) for v in bbox.split(',')]
  except ValueError as e: raise HTTPException(400,'bbox نامعتبر است (minLng,minLat,maxLng,maxLat)') from e
  w+=[Customer.lat.between(y1,y2),Customer.lng.between(x1,x2)]
 rows=s.scalars(select(Customer).where(*w).order_by(Customer.id).limit(limit)).all()
 return {'customers':[{'id':c.id,'code':c.code,'name':c.name,'region':c.region,'lat':c.lat,'lng':c.lng} for c in rows],'without_gps':total_no,'truncated':len(rows)>=limit}

def purge(ctx, s: Session):
 u,cid,r=ctx
 if not has_all(r): raise HTTPException(403,'دسترسی کافی نیست')
 n=purge_gps(s,cid);audit(s,cid,u.id,'purge','gps_points',None,{'deleted':n});s.commit();return {'deleted':n}
