import os,uuid
from datetime import datetime,timedelta,timezone
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_gps.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def role_id(A,name):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==name)
def mkuser(A,role):
 u='g'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'username':u,'password':PW,'name':u,'role_id':role_id(A,role),'company_ids':[]});assert r.status_code==200,r.text;return login(u,PW),r.json()['id']
def cust(A,tag,**kw): return client.post('/api/customers',headers=A,json={'code':tag+uuid.uuid4().hex[:5],'name':tag,'credit_limit':10**9,**kw}).json()
NOW=lambda:datetime.now(timezone.utc)
Z=lambda d:d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def open_cfg(A,**kw):
 """ساعت کاری ۲۴ساعته/همه‌روزه با منطقه‌ی زمانی‌ای که ساعت محلی ≈ ۱۲ ظهر است (تا مرز نیمه‌شب وسط تست نیاید)."""
 n=NOW();m=n.hour*60+n.minute;off=((720-m+720)%1440)-720
 body={'enabled':True,'work_start':'00:00','work_end':'23:59','work_days':[0,1,2,3,4,5,6],'interval_s':60,'min_distance_m':25,'retention_days':90,'tz_offset_min':off,**kw}
 r=client.put('/api/settings/tracking',headers=A,json=body);assert r.status_code==200,r.text;return off,(n+timedelta(minutes=off)).date().isoformat()
def pts(n=8,lat=35.7,lng=51.4,end_min_ago=1,tag=None):
 tag=tag or uuid.uuid4().hex[:6];now=NOW();return [{'client_id':f'{tag}-{i}','lat':lat,'lng':lng,'accuracy_m':8,'recorded_at':Z(now-timedelta(minutes=end_min_ago+(n-1-i)))} for i in range(n)]

def test_ingest_idempotent_and_validation():
 A=login();open_cfg(A);V,_=mkuser(A,'بازاریاب');p=pts(5,tag='idem'+uuid.uuid4().hex[:4])
 r=client.post('/api/gps/points',headers=V,json={'points':p}).json();assert r['stored']==5 and r['duplicate']==0
 r=client.post('/api/gps/points',headers=V,json={'points':p}).json();assert r['stored']==0 and r['duplicate']==5  # ارسال مجدد صف آفلاین بی‌اثر
 bad=[{'lat':35.7,'lng':51.4,'accuracy_m':500},{'lat':35.7,'lng':51.4,'recorded_at':Z(NOW()+timedelta(hours=2))},{'lat':35.7,'lng':51.4,'recorded_at':Z(NOW()-timedelta(days=9))},{'lat':0,'lng':0}]
 r=client.post('/api/gps/points',headers=V,json={'points':bad}).json();assert r['invalid']==4 and r['stored']==0
 assert client.post('/api/gps/points',headers=V,json={'points':[{'lat':95,'lng':0}]}).status_code==422
 assert client.post('/api/gps/points',headers=V,json={'points':[]}).status_code==422
 assert client.post('/api/gps/points',json={'points':p}).status_code==401
def test_outside_work_hours_not_stored_and_disabled():
 A=login();V,_=mkuser(A,'بازاریاب');n=NOW();off,_d=open_cfg(A);wd=(n+timedelta(minutes=off)).weekday()
 open_cfg(A,work_days=[d for d in range(7) if d!=wd])  # امروز تعطیل
 r=client.post('/api/gps/points',headers=V,json={'points':pts(3)}).json();assert r['outside_hours']==3 and r['stored']==0
 assert client.get('/api/gps/config',headers=V).json()['active_now'] is False
 open_cfg(A,enabled=False);r=client.post('/api/gps/points',headers=V,json={'points':pts(3)}).json();assert r['tracking_disabled']==3 and r['stored']==0
 open_cfg(A)
def test_settings_validation_and_permission():
 A=login();V,_=mkuser(A,'بازاریاب');off,_d=open_cfg(A)
 base={'enabled':True,'work_start':'09:00','work_end':'18:00','work_days':[0,1],'interval_s':60,'min_distance_m':25,'retention_days':30,'tz_offset_min':210}
 assert client.put('/api/settings/tracking',headers=V,json=base).status_code==403
 assert client.put('/api/settings/tracking',headers=A,json={**base,'work_start':'18:00','work_end':'09:00'}).status_code==400
 assert client.put('/api/settings/tracking',headers=A,json={**base,'work_days':[1,1]}).status_code==400
 assert client.put('/api/settings/tracking',headers=A,json={**base,'work_days':[9]}).status_code==400
 assert client.put('/api/settings/tracking',headers=A,json={**base,'interval_s':1}).status_code==422
 open_cfg(A)
def test_privacy_scope_and_audit_of_viewing():
 A=login();open_cfg(A);V,vid=mkuser(A,'بازاریاب');M,_=mkuser(A,'مدیر فروش');D,_=mkuser(A,'مأمور پخش')
 client.post('/api/gps/points',headers=V,json={'points':pts(3)})
 for h in (V,D): assert client.get('/api/gps/live',headers=h).status_code==403 and client.get('/api/gps/track',headers=h).status_code==403  # ثبت‌کننده ≠ بیننده
 live=client.get('/api/gps/live',headers=M).json();assert live['active'] and any(u['user_id']==vid and u['kind']=='visitor' for u in live['users'])
 assert client.get(f'/api/gps/track?user_id={vid}',headers=M).status_code==200
 aud=client.get('/api/audit',headers=A).json();assert any(a['entity']=='gps_track' and a['entity_id']==vid and a['action']=='view' for a in aud)
 assert client.get('/api/gps/track?user_id=999999',headers=M).status_code==404
 assert client.get('/api/gps/track?day=2026-13-40',headers=M).status_code==400
 assert client.post('/api/gps/purge',headers=V).status_code==403
def test_track_stays_distance_and_visit_presence():
 A=login();off,day=open_cfg(A);V,vid=mkuser(A,'بازاریاب');M,_=mkuser(A,'مدیر فروش')
 c=cust(A,'GPSC',lat=35.7,lng=51.4);far=cust(A,'GPSF',lat=36.2,lng=52.0)
 assert client.post('/api/gps/points',headers=V,json={'points':pts(9,35.7002,51.4)}).json()['stored']==9
 v=client.post('/api/visits',headers=V,json={'customer_id':c['id'],'lat':35.7002,'lng':51.4});assert v.status_code==200,v.text
 t=client.get(f'/api/gps/track?user_id={vid}&day={day}',headers=M).json()
 assert t['point_count']==9 and t['user']['id']==vid and t['distance_km']<0.2
 assert len(t['stays'])==1 and t['stays'][0]['customer_id']==c['id'] and t['stays'][0]['minutes']>=7
 assert all(s['customer_id']!=far['id'] for s in t['stays'])
 vis=[x for x in t['visits'] if x['customer_id']==c['id']];assert vis and vis[0]['gps_presence'] is True and vis[0]['presence_minutes']>=7
 assert len(client.get(f'/api/gps/track?user_id={vid}&day={day}&max_points=50',headers=M).json()['points'])<=50
 other=(datetime.fromisoformat(day)-timedelta(days=3)).date().isoformat();e=client.get(f'/api/gps/track?user_id={vid}&day={other}',headers=M).json();assert e['point_count']==0 and e['stays']==[] and e['first_at'] is None
def test_visit_without_gps_presence_is_flagged():
 A=login();off,day=open_cfg(A);V,vid=mkuser(A,'بازاریاب');M,_=mkuser(A,'مدیر فروش')
 cust(A,'GPSN',lat=35.7,lng=51.4)
 client.post('/api/gps/points',headers=V,json={'points':pts(9,35.7,51.4)})
 # ویزیتِ ثبت‌شده برای مشتری‌ای که مسیر هرگز نزدیکش نبوده
 far=cust(A,'GPSX',lat=36.5,lng=52.5);v=client.post('/api/visits',headers=V,json={'customer_id':far['id'],'lat':36.5,'lng':52.5});assert v.status_code==200,v.text
 t=client.get(f'/api/gps/track?user_id={vid}&day={day}',headers=M).json();fv=[x for x in t['visits'] if x['customer_id']==far['id']][0];assert fv['gps_presence'] is False
def test_customers_map_bbox_cluster_source_and_access():
 A=login();V,_=mkuser(A,'بازاریاب');c=cust(A,'GPSM',lat=31.5,lng=60.5,region='zz'+uuid.uuid4().hex[:4]);nc=cust(A,'GPSNO')
 d=client.get('/api/gps/customers',headers=V);assert d.status_code==200 and any(x['id']==c['id'] for x in d.json()['customers']) and d.json()['without_gps']>=1
 inb=client.get('/api/gps/customers?bbox=60,31,61,32',headers=V).json()['customers'];assert any(x['id']==c['id'] for x in inb) and all(31<=x['lat']<=32 for x in inb)
 assert not any(x['id']==c['id'] for x in client.get('/api/gps/customers?bbox=10,10,11,11',headers=V).json()['customers'])
 assert client.get('/api/gps/customers?bbox=abc',headers=V).status_code==400
 assert all(x['id']!=nc['id'] for x in d.json()['customers'])
 assert client.get('/api/gps/customers').status_code==401
def test_sync_event_gps_points_offline_batch():
 A=login();off,day=open_cfg(A);V,vid=mkuser(A,'بازاریاب');M,_=mkuser(A,'مدیر فروش');ev={'id':str(uuid.uuid4()),'type':'gps.points','payload':{'points':pts(6,tag='sy'+uuid.uuid4().hex[:4])}}
 r=client.post('/api/sync',headers=V,json={'events':[ev]}).json();assert r['results'][0]['status']=='applied'
 assert client.post('/api/sync',headers=V,json={'events':[ev]}).json()['results'][0]['status']=='duplicate'
 assert client.get(f'/api/gps/track?user_id={vid}&day={day}',headers=M).json()['point_count']==6
 # مأمور بدون gps.record رد می‌شود
 u,_=mkuser(A,'حسابدار');r=client.post('/api/sync',headers=u,json={'events':[{**ev,'id':str(uuid.uuid4())}]}).json();assert r['results'][0]['status']=='rejected'
def test_retention_purge_deletes_only_expired():
 from app.core.database import SessionLocal
 from app.models import GpsPoint
 from app.modules.gps import purge_gps
 A=login();open_cfg(A,retention_days=7);cid=client.get('/api/me',headers=A).json()['company']['id'];V,vid=mkuser(A,'بازاریاب')
 client.post('/api/gps/points',headers=V,json={'points':pts(2)})
 with SessionLocal() as s:
  s.add(GpsPoint(company_id=cid,user_id=vid,client_id='old-'+uuid.uuid4().hex,lat=35.7,lng=51.4,recorded_at=datetime.utcnow()-timedelta(days=30)));s.commit()
  n=purge_gps(s,cid);assert n>=1
  left=s.query(GpsPoint).filter(GpsPoint.company_id==cid,GpsPoint.user_id==vid).count();assert left==2
 assert client.post('/api/gps/purge',headers=A).status_code==200
 open_cfg(A)
