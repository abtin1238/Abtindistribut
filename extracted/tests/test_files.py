import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_files.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
PNG=b'\x89PNG\r\n\x1a\n'+b'0'*50
def test_upload_rules_and_download():
 h=H()
 cid=client.post('/api/customers',headers=h,json={'code':'FILE1','name':'f'}).json()['id']
 up=lambda name,data,ent='customer': client.post(f'/api/documents/upload?entity={ent}&entity_id={cid}',headers=h,files={'file':(name,data)})
 assert up('evil.html',b'<script>alert(1)</script>').status_code==400
 assert up('a.png',PNG,'../etc').status_code==400
 r=up('a.png',PNG); assert r.status_code==200 and 'path' not in r.json()
 d=client.get(f"/api/documents/{r.json()['id']}/download",headers=h); assert d.status_code==200 and d.content==PNG
 assert client.get(f"/api/documents/{r.json()['id']}/download").status_code==401
