import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_driver.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from datetime import date,timedelta
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
PNG=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082')
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def role_id(A,name):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==name)
def driver(A):
 u='d'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'username':u,'password':PW,'name':u,'role_id':role_id(A,'مأمور پخش'),'company_ids':[]});assert r.status_code==200,r.text;return login(u,PW),r.json()['id']
def mission(A,drv_id,tag,qty=4,**cust):
 sfx=uuid.uuid4().hex[:5];c=client.post('/api/customers',headers=A,json={'code':tag+sfx,'name':tag+sfx,'credit_limit':10**9,**cust}).json()
 p=client.post('/api/products',headers=A,json={'sku':tag+sfx,'name':'k'+sfx,'base_price':100}).json();w=client.get('/api/warehouses',headers=A).json()[0]
 client.post('/api/stock/adjust',headers=A,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 o=client.post('/api/orders',headers=A,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':qty}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=A).status_code==200
 d=client.post(f"/api/orders/{o['id']}/assign-delivery",headers=A,json={'order_id':o['id'],'driver_id':drv_id}).json();return c,p,o,d
def inv_of(A,o): return next(i for i in client.get('/api/invoices',headers=A).json() if i['order_id']==o['id'])

def test_mine_scope_route_order_and_detail():
 A=login();D1,d1=driver(A);D2,d2=driver(A)
 a=mission(A,d1,'M1',lat=35.700,lng=51.400);b=mission(A,d1,'M2',lat=35.701,lng=51.401);c=mission(A,d1,'M3',lat=35.800,lng=51.500);e=mission(A,d2,'M4')
 r=client.get('/api/deliveries/mine?lat=35.8&lng=51.5',headers=D1).json()
 assert [x['id'] for x in r['active']]==[c[3]['id'],b[3]['id'],a[3]['id']] and [x['stop'] for x in r['active']]==[1,2,3]
 assert e[3]['id'] not in [x['id'] for x in r['active']] and e[3]['id'] in [x['id'] for x in client.get('/api/deliveries/mine',headers=D2).json()['active']]
 assert client.get(f"/api/deliveries/{e[3]['id']}",headers=D1).status_code==404
 det=client.get(f"/api/deliveries/{a[3]['id']}",headers=D1).json();assert det['invoice_lines'] and det['items'][0]['quantity'] and float(det['invoice']['remaining'])==float(det['invoice']['total'])>=400
 assert client.patch(f"/api/deliveries/{e[3]['id']}",headers=D1,json={'status':'loaded'}).status_code==403
 assert client.get('/api/customers',headers=D1).status_code==403          # مأمور مشتریان را نمی‌بیند

def test_loaded_flow_gps_status_and_signature():
 A=login();D,did=driver(A);c,p,o,d=mission(A,did,'G',lat=35.7,lng=51.4);u=f"/api/deliveries/{d['id']}"
 assert client.patch(u,headers=D,json={'status':'loaded'}).json()['loaded_at']
 assert client.patch(u,headers=D,json={'status':'bogus'}).status_code==400
 assert client.patch(u,headers=D,json={'status':'delivered','lat':35.7002,'lng':51.4,'signature':'data:text/html;base64,xx'}).status_code==400
 r=client.patch(u,headers=D,json={'status':'delivered','lat':35.75,'lng':51.4,'signature':'data:image/png;base64,'+'A'*50});assert r.status_code==200,r.text
 assert r.json()['gps_status']=='out_of_range' and r.json()['distance_m']>5000 and r.json()['delivered_at']
 assert client.patch(u,headers=D,json={'status':'failed','reason':'x'}).status_code==409       # از delivered برگشت ندارد
 done=client.get('/api/deliveries/mine',headers=D).json();assert d['id'] in [x['id'] for x in done['done']] and d['id'] not in [x['id'] for x in done['active']]
 c2,p2,o2,d2=mission(A,did,'G2');assert client.patch(f"/api/deliveries/{d2['id']}",headers=D,json={'status':'delivered'}).json()['gps_status']=='no_customer_gps'
 c3,p3,o3,d3=mission(A,did,'G3',lat=35.7,lng=51.4);assert client.patch(f"/api/deliveries/{d3['id']}",headers=D,json={'status':'delivered','lat':35.7001,'lng':51.4}).json()['gps_status']=='ok'

def test_failed_requires_reason_and_keeps_order_reassignable():
 A=login();D,did=driver(A);c,p,o,d=mission(A,did,'FL');u=f"/api/deliveries/{d['id']}"
 assert client.patch(u,headers=D,json={'status':'failed'}).status_code==400
 assert client.patch(u,headers=D,json={'status':'failed','reason':'مشتری نبود'}).status_code==200
 assert client.patch(u,headers=D,json={'status':'failed','reason':'مشتری نبود'}).status_code==200   # تکرار بی‌اثر
 assert client.post(f"/api/deliveries/{d['id']}/collect",headers=D,json={'amount':10}).status_code==409
 st=next(x for x in client.get('/api/stock',headers=A).json() if x['product_id']==p['id']);assert st['quantity']==50 and st['reserved']==4
 d2=client.post(f"/api/orders/{o['id']}/assign-delivery",headers=A,json={'order_id':o['id'],'driver_id':did}).json();assert d2['id']!=d['id']
 assert any(n['title']=='عدم تحویل' for n in client.get('/api/notifications',headers=A).json())

def test_collect_cash_and_check_on_site():
 A=login();D,did=driver(A);c,p,o,d=mission(A,did,'CL');u=f"/api/deliveries/{d['id']}/collect";inv=inv_of(A,o)
 assert client.post(u,headers=D,json={'amount':500,'method':'cash'}).status_code==400          # بیش از مانده
 assert client.post(u,headers=D,json={'amount':100,'method':'bitcoin'}).status_code==400
 r=client.post(u,headers=D,json={'amount':100,'method':'cash'});assert r.status_code==200 and r.json()['kind']=='payment',r.text
 assert client.post(u,headers=D,json={'amount':100,'method':'check'}).status_code==400          # شماره/سررسید
 due=(date.today()+timedelta(days=30)).isoformat()
 r=client.post(u,headers=D,json={'amount':150,'method':'check','check_number':'CH'+uuid.uuid4().hex[:6],'due_date':due,'bank':'ملی'});assert r.status_code==200 and r.json()['kind']=='check',r.text
 assert client.post(u,headers=D,json={'amount':999,'method':'check','check_number':'X','due_date':due}).status_code==400
 i=next(x for x in client.get('/api/invoices',headers=A).json() if x['id']==inv['id']);assert float(i['paid'])==100
 D2,_=driver(A);assert client.post(u,headers=D2,json={'amount':10}).status_code==404                # ماموریت دیگری
 assert client.get('/api/reports/trial-balance',headers=A).json()['balanced']

def test_photo_upload_type_and_ownership():
 A=login();D,did=driver(A);D2,_=driver(A);c,p,o,d=mission(A,did,'PH');u=f"/api/deliveries/{d['id']}/photo"
 assert client.post(u,headers=D,files={'file':('x.png',PNG,'image/png')}).status_code==200
 assert client.post(u,headers=D,files={'file':('x.png',b'<html>evil</html>','image/png')}).status_code==400
 assert client.post(u,headers=D2,files={'file':('x.png',PNG,'image/png')}).status_code==404
 assert client.get(f"/api/deliveries/{d['id']}",headers=D).json()['proof_photo'].startswith('/api/documents/')

def test_sync_driver_events_loaded_collect_delivered():
 A=login();D,did=driver(A);c,p,o,d=mission(A,did,'SY');u=uuid.uuid4().hex[:6]
 r=client.post('/api/sync',headers=D,json={'events':[{'id':'l'+u,'type':'delivery.loaded','entity_id':d['id']},{'id':'c'+u,'type':'delivery.collect','entity_id':d['id'],'payload':{'amount':100,'method':'cash'}},
  {'id':'d'+u,'type':'delivery.delivered','entity_id':d['id'],'payload':{'items':[{'product_id':p['id'],'quantity':3}],'reason':'یک عدد شکسته'}}]}).json()
 assert [x['status'] for x in r['results']]==['applied']*3,r
 i=inv_of(A,o);assert float(i['returned'])>=100 and float(i['paid'])==100
 assert client.get('/api/reports/trial-balance',headers=A).json()['balanced']
