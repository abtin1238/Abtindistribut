import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_test_v3.sqlite3'
try: os.remove('/tmp/abtin_dist_test_v3.sqlite3')
except FileNotFoundError: pass
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
 r=client.get('/health'); assert r.status_code==200 and r.json()['ok'] is True
def test_login_and_me():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200
 t=r.json()['token']; m=client.get('/api/me',headers={'Authorization':'Bearer '+t}); assert m.status_code==200; assert m.json()['company']['name']=='شرکت پخش نمونه'
def test_tenant_org():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); t=r.json()['token']; d=client.get('/api/organizations',headers={'Authorization':'Bearer '+t}).json(); assert len(d['companies'])>=1
