import os,uuid,threading
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_conc.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
import pytest
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def setup(h,qty=10):
 t=uuid.uuid4().hex[:6]
 c=client.post('/api/customers',headers=h,json={'code':'K'+t,'name':'m','credit_limit':10**8}).json()
 p=client.post('/api/products',headers=h,json={'sku':'K'+t,'name':'k','base_price':100}).json()
 w=client.post('/api/warehouses',headers=h,json={'company_id':client.get('/api/me',headers=h).json()['company']['id'],'name':'W'+t}).json()
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':qty,'kind':'in'})
 return c,p,w
def order(h,c,p,w,q):
 return client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q}]}).json()
def st(h,p,w): return next(x for x in client.get('/api/stock',headers=h).json() if x['product_id']==p['id'] and x['warehouse_id']==w['id'])
def test_no_oversell_on_last_stock_sequential():
 h=H();c,p,w=setup(h,10);o1=order(h,c,p,w,6);o2=order(h,c,p,w,6)
 assert client.post(f"/api/orders/{o1['id']}/approve",headers=h).status_code==200
 assert client.post(f"/api/orders/{o2['id']}/approve",headers=h).status_code==400
 s=st(h,p,w);assert float(s['reserved'])==6 and float(s['available'])==4
 assert client.post(f"/api/orders/{o1['id']}/cancel",headers=h).status_code==200
 assert client.post(f"/api/orders/{o2['id']}/approve",headers=h).status_code==200
 assert float(st(h,p,w)['reserved'])==6
def test_double_approve_and_double_cancel_do_not_double_reserve():
 h=H();c,p,w=setup(h,10);o=order(h,c,p,w,3)
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==400
 assert float(st(h,p,w)['reserved'])==3
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=h).status_code==200
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=h).status_code==400
 assert float(st(h,p,w)['reserved'])==0
def test_stock_equals_sum_of_moves():
 h=H();c,p,w=setup(h,10)
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':4,'kind':'out','reason':'کسری'})
 assert float(st(h,p,w)['quantity'])==6
 assert client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':7,'kind':'out','reason':'کسری'}).status_code==400
@pytest.mark.skipif(not os.environ['DATABASE_URL'].startswith('postgres'),reason='نیازمند PostgreSQL برای قفل ردیف واقعی')
def test_parallel_approvals_on_last_stock_postgres():
 h=H();c,p,w=setup(h,10);orders=[order(h,c,p,w,6) for _ in range(4)];codes=[]
 def go(o):
  with TestClient(app) as cl: codes.append(cl.post(f"/api/orders/{o['id']}/approve",headers=h).status_code)
 ts=[threading.Thread(target=go,args=(o,)) for o in orders]
 [t.start() for t in ts];[t.join() for t in ts]
 assert codes.count(200)==1 and float(st(h,p,w)['reserved'])==6
