import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_scope.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def seller_role(A):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']=='فروشنده')
def mk(A,role,branch=None):
 u='s'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'username':u,'password':PW,'name':u,'role_id':role,'company_ids':[],'branch_id':branch});assert r.status_code==200,r.text;return login(u,PW)
def test_branch_scope_and_own_leads():
 A=login();sfx=uuid.uuid4().hex[:5];cid=client.get('/api/me',headers=A).json()['company']['id']
 ba=client.post('/api/organizations/branch',headers=A,json={'company_id':cid,'name':'A'+sfx}).json()['id'];bb=client.post('/api/organizations/branch',headers=A,json={'company_id':cid,'name':'B'+sfx}).json()['id']
 wa=client.post('/api/warehouses',headers=A,json={'company_id':cid,'branch_id':ba,'name':'WA'+sfx}).json()['id'];wb=client.post('/api/warehouses',headers=A,json={'company_id':cid,'branch_id':bb,'name':'WB'+sfx}).json()['id']
 p=client.post('/api/products',headers=A,json={'sku':'P'+sfx,'name':'k','base_price':10}).json()['id'];c=client.post('/api/customers',headers=A,json={'code':'C'+sfx,'name':'m','credit_limit':100000}).json()['id']
 for w in (wa,wb): assert client.post('/api/stock/adjust',headers=A,json={'warehouse_id':w,'product_id':p,'quantity':10,'kind':'in'}).status_code==200
 role=seller_role(A);S1=mk(A,role,ba);S2=mk(A,role,bb);S0=mk(A,role)
 ids=lambda H:{w['id'] for w in client.get('/api/warehouses',headers=H).json()}
 assert wa in ids(S1) and wb not in ids(S1) and wb in ids(S2) and wa not in ids(S2) and {wa,wb}<=ids(S0)<=ids(A)
 assert {x['warehouse_id'] for x in client.get('/api/stock',headers=S1).json()}.isdisjoint({wb})
 assert {x['warehouse_id'] for x in client.get('/api/reports/stock',headers=A).json()['items']}>={wa,wb}
 body=lambda w:{'customer_id':c,'warehouse_id':w,'items':[{'product_id':p,'quantity':1}]}
 assert client.post('/api/orders',headers=S1,json=body(wb)).status_code==404
 o=client.post('/api/orders',headers=S1,json=body(wa));assert o.status_code==200,o.text
 assert client.post(f"/api/orders/{o.json()['id']}/approve",headers=S2).status_code in (403,404)
 assert any(x['id']==o.json()['id'] for x in client.get('/api/orders',headers=S1).json())
 assert all(x['warehouse_id']==wa for x in client.get('/api/orders',headers=S1).json())
 # انباردارِ ندارای data.all نیز نباید انبار شعبه‌ی دیگر را تعدیل کند
 assert client.post('/api/stock/adjust',headers=S1,json={'warehouse_id':wb,'product_id':p,'quantity':1,'kind':'in'}).status_code in (403,404)
 # شعبه‌ی شرکت دیگر/ناموجود رد می‌شود
 assert client.post('/api/users',headers=A,json={'username':'x'+sfx,'password':PW,'name':'x','role_id':role,'company_ids':[],'branch_id':999999}).status_code==404
 # leads: own
 l=client.post('/api/leads',headers=S1,json={'title':'L'+sfx}).json()
 assert any(x['id']==l['id'] for x in client.get('/api/leads',headers=S1).json())
 assert all(x['id']!=l['id'] for x in client.get('/api/leads',headers=S2).json())
 assert any(x['id']==l['id'] for x in client.get('/api/leads',headers=A).json())
