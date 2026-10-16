import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_lockout.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_account_locks_after_failed_attempts():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 H={'Authorization':'Bearer '+r.json()['token']}
 role=next(x['id'] for x in client.get('/api/roles',headers=H).json() if '*' not in (x['permissions'] or []))
 assert client.post('/api/users',headers=H,json={'username':'lockme','password':'Lock-pass-1','name':'l','role_id':role,'company_ids':[1]}).status_code==200
 for _ in range(5): assert client.post('/api/auth/login',json={'username':'lockme','password':'bad'}).status_code==401
 assert client.post('/api/auth/login',json={'username':'lockme','password':'Lock-pass-1'}).status_code==429
