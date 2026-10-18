import os
from datetime import datetime, timedelta
from app.services.geo import evaluate_geofences
Z=[{'id':1,'lat':35.7000,'lng':51.4000,'radius_m':100}]
T0=datetime(2026,3,2,6,0)
def pt(i,lat,lng): return {'lat':lat,'lng':lng,'t':T0+timedelta(minutes=i)}
FAR=35.7100; NEAR=35.7000; EDGE=35.7000+0.00095   # ≈۱۰۵ متر: خارج شعاع ولی داخل هیسترزیس

def test_enter_then_exit():
 ev,ins=evaluate_geofences([pt(0,FAR,51.4),pt(1,NEAR,51.4),pt(2,NEAR,51.4),pt(3,FAR,51.4)],Z,set())
 assert [e['kind'] for e in ev]==['enter','exit'] and ev[0]['t']==T0+timedelta(minutes=1) and ins==set()

def test_hysteresis_no_flapping_at_boundary():
 ev,ins=evaluate_geofences([pt(0,NEAR,51.4),pt(1,EDGE,51.4),pt(2,NEAR,51.4)],Z,set())
 assert [e['kind'] for e in ev]==['enter'] and ins=={1}

def test_initial_inside_state_prevents_duplicate_enter():
 ev,ins=evaluate_geofences([pt(0,NEAR,51.4)],Z,{1}); assert ev==[] and ins=={1}

def test_invalid_points_ignored_and_multi_zone():
 zs=Z+[{'id':2,'lat':35.7100,'lng':51.4,'radius_m':100}]
 ev,_=evaluate_geofences([pt(0,0,0),pt(1,NEAR,51.4),pt(2,FAR,51.4)],zs,set())
 assert [(e['geofence_id'],e['kind']) for e in ev]==[(1,'enter'),(1,'exit'),(2,'enter')]

# --- API (نیازمند fastapi) ---
def _client():
 os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_gf.sqlite3'); os.environ['ADMIN_PASSWORD']='test-password'
 from fastapi.testclient import TestClient
 from app.main import app
 c=TestClient(app); r=c.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return c,{'Authorization':'Bearer '+r.json()['token']}

def test_geofence_crud_and_ingest_creates_events():
 c,h=_client()
 c.put('/api/settings/tracking',headers=h,json={'enabled':True,'work_days':[0,1,2,3,4,5,6],'work_start':'00:00','work_end':'23:59'})
 g=c.post('/api/geofences',headers=h,json={'name':'انبار-T','kind':'depot','lat':35.7,'lng':51.4,'radius_m':100}); assert g.status_code==200,g.text
 assert c.post('/api/geofences',headers=h,json={'name':'انبار-T','lat':35.7,'lng':51.4,'radius_m':100}).status_code==409
 assert c.post('/api/geofences',headers=h,json={'name':'bad','lat':95,'lng':51.4,'radius_m':100}).status_code==422
 now=datetime.utcnow()
 pts=[{'lat':35.71,'lng':51.4,'recorded_at':(now-timedelta(minutes=3)).isoformat(),'client_id':'gf-a'},{'lat':35.7,'lng':51.4,'recorded_at':(now-timedelta(minutes=2)).isoformat(),'client_id':'gf-b'},{'lat':35.71,'lng':51.4,'recorded_at':(now-timedelta(minutes=1)).isoformat(),'client_id':'gf-c'}]
 r=c.post('/api/gps/points',headers=h,json={'points':pts}); assert r.status_code==200 and r.json()['stored']==3,r.text
 ev=c.get(f'/api/geofences/events?geofence_id={g.json()["id"]}',headers=h).json()
 assert [e['kind'] for e in reversed(ev)]==['enter','exit'] and ev[0]['geofence']=='انبار-T'
 assert c.delete(f'/api/geofences/{g.json()["id"]}',headers=h).json()['active'] is False
