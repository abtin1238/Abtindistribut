import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_delete.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def role_id(A,name):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==name)
def mkuser(A,role='فروشنده',**kw):
 u='x'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'branch_id':1,'username':u,'password':PW,'name':u,'role_id':role_id(A,role),'company_ids':[],**kw});assert r.status_code==200,r.text;return u,r.json()['id']

def test_deletable_list_super_only():
 A=login();assert 'leads' in client.get('/api/deletable',headers=A).json()
 u,_=mkuser(A);assert client.get('/api/deletable',headers=login(u,PW)).status_code==403

def test_delete_lead_and_children():
 A=login();l=client.post('/api/leads',headers=A,json={'title':'بالقوه'}).json()
 client.post(f"/api/leads/{l['id']}/activities",headers=A,json={'kind':'note','note':'x'})
 assert client.delete(f"/api/leads/{l['id']}",headers=A).status_code==200
 assert all(x['id']!=l['id'] for x in client.get('/api/leads',headers=A).json())
 assert client.delete(f"/api/leads/{l['id']}",headers=A).status_code==404

def test_delete_blocked_by_dependents_and_non_super():
 A=login();c=client.post('/api/customers',headers=A,json={'code':'D'+uuid.uuid4().hex[:5],'name':'c'}).json()
 l=client.post('/api/leads',headers=A,json={'title':'t','customer_id':c['id']}).json()
 r=client.delete(f"/api/customers/{c['id']}",headers=A);assert r.status_code==409
 u,_=mkuser(A);assert client.delete(f"/api/leads/{l['id']}",headers=login(u,PW)).status_code==403
 assert client.delete(f"/api/leads/{l['id']}",headers=A).status_code==200
 assert client.delete(f"/api/customers/{c['id']}",headers=A).status_code==200

def test_delete_user_and_role():
 A=login();u,uid=mkuser(A)
 assert client.delete(f'/api/users/{uid}',headers=A).status_code==200
 assert all(x['id']!=uid for x in client.get('/api/users',headers=A).json())
 assert client.post('/api/auth/login',json={'username':u,'password':PW}).status_code in (401,403)
 me=client.get('/api/me',headers=A).json()['user']['id'];assert client.delete(f'/api/users/{me}',headers=A).status_code==400
 rid=client.post('/api/roles',headers=A,json={'name':'tmp'+uuid.uuid4().hex[:4],'permissions':['crm.read']}).json()['id']
 assert client.delete(f'/api/roles/{rid}',headers=A).status_code==200

def test_funnel_by_customer():
 A=login();c=client.post('/api/customers',headers=A,json={'code':'F'+uuid.uuid4().hex[:5],'name':'مشتری قیف'}).json()
 client.post('/api/leads',headers=A,json={'title':'a','customer_id':c['id'],'value':100});client.post('/api/leads',headers=A,json={'title':'b','value':5})
 rows=client.get('/api/automation/funnel',headers=A).json()['by_customer']
 mine=next(x for x in rows if x['customer_id']==c['id']);assert mine['name']=='مشتری قیف' and mine['total']==1 and mine['open']==1
 assert any(x['customer_id'] is None for x in rows)
