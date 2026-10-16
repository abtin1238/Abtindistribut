import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_fixes.sqlite3');os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def login(u='admin',p='test-password'):
 r=client.post('/api/auth/login',json={'username':u,'password':p});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def make(H,code,qty=3):
 c=client.post('/api/customers',headers=H,json={'code':code,'name':'م','credit_limit':1000000}).json()
 p=client.post('/api/products',headers=H,json={'sku':code,'name':'ک','base_price':100}).json()
 w=client.get('/api/warehouses',headers=H).json()[0]
 client.post('/api/stock/adjust',headers=H,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 o=client.post('/api/orders',headers=H,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':qty}]}).json()
 return c,p,o
def bal(H,i): return float(next(c for c in client.get('/api/customers',headers=H).json() if c['id']==i)['balance'])
def res(H,i): return float(next(x for x in client.get('/api/stock',headers=H).json() if x['product_id']==i)['reserved'])
def test_balance_and_cancel():
 H=login();c,p,o=make(H,'F1')
 assert client.post(f"/api/orders/{o['id']}/approve",headers=H).status_code==200
 assert bal(H,c['id'])==300 and res(H,p['id'])==3
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=H).status_code==200
 assert bal(H,c['id'])==0 and res(H,p['id'])==0
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=H).status_code==400
def test_paid_order_cannot_cancel():
 H=login();c,p,o=make(H,'F2');client.post(f"/api/orders/{o['id']}/approve",headers=H)
 inv=[i for i in client.get('/api/invoices',headers=H).json() if i['order_id']==o['id']][0]
 assert client.post('/api/payments',headers=H,json={'customer_id':c['id'],'invoice_id':inv['id'],'amount':50,'kind':'receipt'}).status_code==200
 assert bal(H,c['id'])==250 and client.post(f"/api/orders/{o['id']}/cancel",headers=H).status_code==400
def test_permissions_enforced():
 H=login();r=client.post('/api/roles',headers=H,json={'name':'فقط‌خواندن','permissions':['crm.read']}).json()
 assert client.post('/api/users',headers=H,json={'username':'ro','password':'Ro-pass-1','name':'ر','role_id':r['id'],'company_ids':[1]}).status_code==200
 R=login('ro','Ro-pass-1')
 assert client.get('/api/customers',headers=R).status_code==200 and client.get('/api/me',headers=R).status_code==200
 assert client.get('/api/settings/brand',headers=R).status_code==200
 for method,url in [('post','/api/payments'),('post','/api/orders/1/approve'),('post','/api/journal'),('get','/api/audit'),('post','/api/stock/adjust'),('put','/api/settings/brand')]:
  assert client.request(method.upper(),url,headers=R,json={}).status_code==403,url
def role_id(H,name): return next(r['id'] for r in client.get('/api/roles',headers=H).json() if r['name']==name)
def mkuser(H,u,role): assert client.post('/api/users',headers=H,json={'username':u,'password':'Pw-test-1','name':u,'role_id':role,'company_ids':[1]}).status_code==200;return login(u,'Pw-test-1')
def test_escalation_blocked():
 H=login();r=client.post('/api/roles',headers=H,json={'name':'مدیر‌کاربران','permissions':['admin.write','crm.read']}).json()
 M=mkuser(H,'mgr1',r['id'])
 for perms in (['*'],['finance.write'],['bogus.code']): assert client.post('/api/roles',headers=M,json={'name':'x','permissions':perms}).status_code in (400,403),perms
 assert client.post('/api/roles',headers=M,json={'name':'ok','permissions':['crm.read']}).status_code==200
 admin_role=next(x['id'] for x in client.get('/api/roles',headers=H).json() if '*' in (x['permissions'] or []))
 assert client.post('/api/users',headers=M,json={'username':'evil','password':'Pw-test-1','name':'e','role_id':admin_role,'company_ids':[1]}).status_code==403
 assert 'password_hash' not in client.get('/api/users',headers=H).json()[0]
def test_data_scope_and_collect():
 H=login();c,p,o=make(H,'F3');V=mkuser(H,'vis1',role_id(H,'بازاریاب'))
 w=client.get('/api/warehouses',headers=H).json()[0]
 mine=client.post('/api/orders',headers=V,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}).json()
 ids={x['id'] for x in client.get('/api/orders',headers=V).json()};assert mine['id'] in ids and o['id'] not in ids
 assert o['id'] in {x['id'] for x in client.get('/api/orders',headers=H).json()}
 assert client.post(f"/api/orders/{o['id']}/approve",headers=V).status_code==403
 assert client.post('/api/payments',headers=V,json={'customer_id':c['id'],'amount':10,'kind':'refund'}).status_code==403
 assert client.post('/api/payments',headers=V,json={'customer_id':c['id'],'amount':10,'kind':'receipt'}).status_code==200
 assert client.get('/api/users',headers=V).status_code==403 and client.get('/api/journal',headers=V).status_code==403
