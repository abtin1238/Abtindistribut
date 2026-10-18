import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19auth.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def login(pw='test-password'):
 r=client.post('/api/auth/login',json={'username':'admin','password':pw}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_logout_revokes_token():
 H=login(); assert client.get('/api/me',headers=H).status_code==200
 assert client.post('/api/auth/logout',headers=H).status_code==200
 assert client.get('/api/me',headers=H).status_code==401

def test_sessions_list_and_logout_all_keeps_current():
 H1=login(); H2=login()
 rows=client.get('/api/auth/sessions',headers=H1).json(); assert len(rows)>=2 and sum(1 for r in rows if r['current'])==1
 assert client.post('/api/auth/logout-all',headers=H1).json()['revoked']>=1
 assert client.get('/api/me',headers=H2).status_code==401 and client.get('/api/me',headers=H1).status_code==200

def test_change_password_rules_and_revocation():
 H=login(); H2=login()
 assert client.post('/api/auth/change-password',headers=H,json={'old_password':'bad','new_password':'Another-pass-12'}).status_code==400
 assert client.post('/api/auth/change-password',headers=H,json={'old_password':'test-password','new_password':'test-password'}).status_code==400
 assert client.post('/api/auth/change-password',headers=H,json={'old_password':'test-password','new_password':'admin'}).status_code==400
 r=client.post('/api/auth/change-password',headers=H,json={'old_password':'test-password','new_password':'Another-pass-12'}); assert r.status_code==200,r.text
 assert client.get('/api/me',headers=H2).status_code==401 and client.get('/api/me',headers=H).status_code==200
 assert client.post('/api/auth/login',json={'username':'admin','password':'test-password'}).status_code==401
 H3=login('Another-pass-12')
 assert client.post('/api/auth/change-password',headers=H3,json={'old_password':'Another-pass-12','new_password':'test-password'}).status_code==200
