import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_custupd.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text
 return r.json()
def H(d): return {'Authorization':'Bearer '+d['token']}
def role_id(h,name):
 client.post('/api/roles/templates',headers=h)
 return next(r['id'] for r in client.get('/api/roles',headers=h).json() if r['name']==name)
def mk_user(h,role,branch):
 u='u'+uuid.uuid4().hex[:8]
 r=client.post('/api/users',headers=h,json={'username':u,'password':PW,'name':u,'role_id':role_id(h,role),'company_ids':[],'branch_id':branch});assert r.status_code==200,r.text
 return u
def test_customer_can_be_edited_and_moved_between_branches():
 h=H(login());cid=client.get('/api/me',headers=h).json()['company']['id']
 a=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'EA'}).json()['id']
 b=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'EB'}).json()['id']
 c=client.post('/api/customers',headers=h,json={'code':'U'+uuid.uuid4().hex[:6],'name':'قدیمی','branch_id':a}).json()
 r=client.patch(f"/api/customers/{c['id']}",headers=h,json={'name':'جدید','branch_id':b,'credit_limit':'500'});assert r.status_code==200,r.text
 assert r.json()['name']=='جدید' and r.json()['branch_id']==b
 assert client.patch(f"/api/customers/{c['id']}",headers=h,json={}).status_code==400
 assert client.patch(f"/api/customers/{c['id']}",headers=h,json={'branch_id':999999}).status_code==404
def test_branch_manager_cannot_move_customer_out_of_branch_or_touch_other_branch():
 h=H(login());cid=client.get('/api/me',headers=h).json()['company']['id']
 a=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'MA'}).json()['id']
 b=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'MB'}).json()['id']
 ca=client.post('/api/customers',headers=h,json={'code':'A'+uuid.uuid4().hex[:6],'name':'در A','branch_id':a}).json()['id']
 cb=client.post('/api/customers',headers=h,json={'code':'B'+uuid.uuid4().hex[:6],'name':'در B','branch_id':b}).json()['id']
 mh=H(login(mk_user(h,'مدیر شرکت',a),PW))
 assert client.patch(f'/api/customers/{ca}',headers=mh,json={'phone':'021'}).status_code==200
 assert client.patch(f'/api/customers/{ca}',headers=mh,json={'branch_id':b}).status_code==403
 assert client.patch(f'/api/customers/{ca}',headers=mh,json={'branch_id':None}).status_code==403
 assert client.patch(f'/api/customers/{cb}',headers=mh,json={'phone':'021'}).status_code==404
