import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_brand.sqlite3');os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
PNG=b'\x89PNG\r\n\x1a\n'+b'0'*50
def h():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});return {'Authorization':'Bearer '+r.json()['token']}
def test_brand_and_logo():
 H=h();b=client.put('/api/settings/brand',headers=H,json={'name':'برند من','tagline':'شعار','color':'#ff0000'}).json();assert b['name']=='برند من' and b['color']=='#ff0000'
 assert client.put('/api/settings/brand',headers=H,json={'color':'red'}).status_code==422
 assert client.post('/api/settings/logo',headers=H,files={'file':('a.svg',b'<svg onload=1>','image/svg+xml')}).status_code==400
 b=client.post('/api/settings/logo',headers=H,files={'file':('a.png',PNG,'image/png')}).json();assert b['has_logo']
 g=client.get(b['logo_url']);assert g.status_code==200 and g.headers['content-type']=='image/png'
 assert client.delete('/api/settings/logo',headers=H).json()['has_logo'] is False
