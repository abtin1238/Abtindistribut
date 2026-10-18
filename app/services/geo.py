"""توابع خالص جغرافیایی و مسیر؛ بدون وابستگی به دیتابیس (قابل تست مستقل)."""
from __future__ import annotations
from math import asin,cos,radians,sin,sqrt
from typing import Optional,Sequence

DEFAULT_RADIUS_M=150.0
def haversine_m(lat1,lng1,lat2,lng2)->float:
 p1,p2=radians(lat1),radians(lat2);dp=p2-p1;dl=radians(lng2-lng1)
 a=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
 return 2*6371008.8*asin(min(1.0,sqrt(a)))
def valid_point(lat,lng)->bool:
 return lat is not None and lng is not None and -90<=lat<=90 and -180<=lng<=180 and not (lat==0 and lng==0)
def gps_check(v_lat,v_lng,c_lat,c_lng,radius_m=DEFAULT_RADIUS_M):
 """(distance_m|None, status) ؛ status یکی از ok/out_of_range/no_visit_gps/no_customer_gps"""
 if not valid_point(c_lat,c_lng): return None,'no_customer_gps'
 if not valid_point(v_lat,v_lng): return None,'no_visit_gps'
 d=haversine_m(v_lat,v_lng,c_lat,c_lng)
 return round(d,1),('ok' if d<=radius_m else 'out_of_range')
def suggest_route(cands:Sequence[dict],limit:int=20,start:Optional[tuple]=None)->list[dict]:
 """cands: [{id,lat,lng,last_visit(date|None)}]. ابتدا `limit` مشتریِ قدیمی‌ترین ویزیت (هرگز‌ندیده‌ها اول؛ تساوی با id)
 انتخاب می‌شود تا پوشش مشتریان حفظ شود، سپس با نزدیک‌ترین‌همسایه از نقطه‌ی شروع مرتب می‌شود. مشتریان بدون مختصات آخر می‌آیند."""
 from datetime import date
 pick=sorted(cands,key=lambda c:(c.get('last_visit') or date.min,c['id']))[:max(0,limit)]
 withgps=[c for c in pick if valid_point(c.get('lat'),c.get('lng'))];nogps=[c for c in pick if not valid_point(c.get('lat'),c.get('lng'))]
 order=[];cur=start if start and valid_point(*start) else None
 if cur is None and withgps:
  first=withgps[0];withgps=withgps[1:];order.append((first,0.0));cur=(first['lat'],first['lng'])
 left=list(withgps)
 while left:
  nxt=min(left,key=lambda c:(haversine_m(cur[0],cur[1],c['lat'],c['lng']),c['id']));d=haversine_m(cur[0],cur[1],nxt['lat'],nxt['lng'])
  order.append((nxt,d));cur=(nxt['lat'],nxt['lng']);left.remove(nxt)
 order+=[(c,None) for c in nogps]
 return [{**c,'sequence':i,'distance_km':None if d is None else round(d/1000,2)} for i,(c,d) in enumerate(order,1)]
def nn_order(cands:Sequence[dict],start:Optional[tuple]=None)->list[dict]:
 """همه‌ی کاندیدها (با کلید id/lat/lng) را با نزدیک‌ترین‌همسایه مرتب می‌کند؛ بدون مختصات آخر و به ترتیب id."""
 gps=[c for c in cands if valid_point(c.get('lat'),c.get('lng'))];no=sorted((c for c in cands if not valid_point(c.get('lat'),c.get('lng'))),key=lambda c:c['id'])
 cur=start if start and valid_point(*start) else None;out=[]
 if cur is None and gps: f=min(gps,key=lambda c:c['id']);gps=[c for c in gps if c is not f];out.append(f);cur=(f['lat'],f['lng'])
 while gps:
  n=min(gps,key=lambda c:(haversine_m(cur[0],cur[1],c['lat'],c['lng']),c['id']));out.append(n);cur=(n['lat'],n['lng']);gps=[c for c in gps if c is not n]
 return out+no

# ───────── مرحله ۱۳: ردیابی، مسافت، زمان حضور (توابع خالص) ─────────
MAX_SPEED_MPS=70.0   # بیش از ~۲۵۰ km/h = پرش نامعتبر GPS
MAX_ACCURACY_M=200.0 # نقطه با دقت بدتر از این ذخیره نمی‌شود
def track_distance_m(pts:Sequence[dict])->float:
 """مسافت مسیر؛ نقاط به ترتیب زمان. قطعه‌های با سرعت غیرممکن (پرش GPS) شمرده نمی‌شوند."""
 tot=0.0;prev=None
 for p in pts:
  if not valid_point(p.get('lat'),p.get('lng')): continue
  if prev is not None:
   d=haversine_m(prev['lat'],prev['lng'],p['lat'],p['lng']);dt=(p['t']-prev['t']).total_seconds()
   if dt>0 and d/dt<=MAX_SPEED_MPS: tot+=d
   elif dt<=0: continue
  prev=p
 return round(tot,1)
def detect_stays(pts:Sequence[dict],places:Sequence[dict],radius_m:float=DEFAULT_RADIUS_M,min_minutes:float=3.0,max_gap_min:float=15.0)->list[dict]:
 """زمان حضور نزد مشتری از نقاط GPS.
 pts: [{lat,lng,t(datetime)}] مرتب‌شده؛ places: [{id,name,lat,lng,radius_m?}].
 هر نقطه به نزدیک‌ترین مکانی که داخل شعاعش است نسبت داده می‌شود؛ نقاط پیاپیِ همان مکان (با فاصله‌ی زمانی ≤ max_gap_min)
 یک «حضور» می‌شوند. حضورهای کوتاه‌تر از min_minutes حذف می‌شوند (عبور از کنار مشتری). خروجی به ترتیب زمان ورود."""
 pl=[p for p in places if valid_point(p.get('lat'),p.get('lng'))];out=[];cur=None
 def close():
  nonlocal cur
  if cur and (cur['exit']-cur['enter']).total_seconds()/60>=min_minutes:
   cur['minutes']=round((cur['exit']-cur['enter']).total_seconds()/60,1);out.append(cur)
  cur=None
 for p in pts:
  if not valid_point(p.get('lat'),p.get('lng')): continue
  best=None;bd=None
  for c in pl:
   d=haversine_m(p['lat'],p['lng'],c['lat'],c['lng']);r=c.get('radius_m') or radius_m
   if d<=r and (bd is None or d<bd): best,bd=c,d
  if cur and (p['t']-cur['exit']).total_seconds()/60>max_gap_min: close()
  if best is None: close();continue
  if cur and cur['place_id']!=best['id']: close()
  if cur is None: cur={'place_id':best['id'],'name':best.get('name',''),'enter':p['t'],'exit':p['t'],'points':1,'min_distance_m':round(bd,1)}
  else: cur['exit']=p['t'];cur['points']+=1;cur['min_distance_m']=min(cur['min_distance_m'],round(bd,1))
 close();return out
def thin_points(pts:Sequence[dict],limit:int)->list[dict]:
 """کاهش تعداد نقاط برای نمایش (حفظ اولین و آخرین نقطه)."""
 n=len(pts)
 if limit<2 or n<=limit: return list(pts)
 step=(n-1)/(limit-1);return [pts[round(i*step)] for i in range(limit)]

def evaluate_geofences(pts:Sequence[dict],zones:Sequence[dict],inside:set,exit_factor:float=1.1)->tuple[list[dict],set]:
 """رویدادهای ورود/خروج ناحیه‌ها برای نقاط مرتب‌شدهٔ یک کاربر. zones: [{id,lat,lng,radius_m}]؛ inside: مجموعهٔ id ناحیه‌هایی که کاربر قبلاً داخلشان بوده.
 هیسترزیس: ورود در d<=r، خروج فقط وقتی d>r*exit_factor (جلوگیری از لرزش مرز). خروجی: (events[{geofence_id,kind,t,lat,lng}], inside جدید)."""
 inside=set(inside);ev=[]
 for p in pts:
  if not valid_point(p.get('lat'),p.get('lng')): continue
  for z in zones:
   d=haversine_m(p['lat'],p['lng'],z['lat'],z['lng']);r=z['radius_m'];zid=z['id']
   if zid not in inside and d<=r: inside.add(zid);ev.append({'geofence_id':zid,'kind':'enter','t':p['t'],'lat':p['lat'],'lng':p['lng']})
   elif zid in inside and d>r*exit_factor: inside.discard(zid);ev.append({'geofence_id':zid,'kind':'exit','t':p['t'],'lat':p['lat'],'lng':p['lng']})
 return ev,inside
