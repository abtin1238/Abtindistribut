import os,tempfile
os.environ.pop('ADMIN_PASSWORD',None);os.environ.pop('SETUP_TOKEN',None);os.environ.pop('APP_ENV',None)
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(),'setup.sqlite3')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_first_run_defines_super_admin_once():
 assert client.get('/api/auth/setup-status').json()['needs_setup'] is True
 assert client.post('/api/auth/login',json={'username':'admin','password':'x'}).status_code==401
 assert client.post('/api/auth/setup',json={'name':'م','username':'boss','password':'short'}).status_code==400
 r=client.post('/api/auth/setup',json={'name':'مدیر','username':'boss','password':'Strong-pass-1','company_name':'شرکت من'});assert r.status_code==200,r.text
 assert client.get('/api/auth/setup-status').json()['needs_setup'] is False
 assert client.post('/api/auth/setup',json={'name':'x','username':'evil','password':'Strong-pass-2'}).status_code==409
 t=client.post('/api/auth/login',json={'username':'boss','password':'Strong-pass-1'});assert t.status_code==200,t.text
 h={'Authorization':'Bearer '+t.json()['token']};me=client.get('/api/me',headers=h).json()
 assert me['user']['permissions']==['*'] and me['user']['branch_id'] is None and me['company']['name']=='شرکت من'
 assert client.get('/api/users',headers=h).status_code==200
