import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_sync.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_sync.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def base(h,tag):
 c=client.post('/api/customers',headers=h,json={'code':tag,'name':tag,'credit_limit':10**8}).json()
 p=client.post('/api/products',headers=h,json={'sku':tag,'name':tag,'base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':20,'kind':'in'})
 return c,p,w
def sync(h,*events): return client.post('/api/sync',headers=h,json={'events':list(events)}).json()
def test_offline_visit_start_then_finish_by_ref_and_idempotent():
 h=H();c,p,w=base(h,'S1')
 r=sync(h,{'id':'v-start-1','type':'visit.start','payload':{'customer_id':c['id'],'lat':35.7,'lng':51.4,'started_at':'2026-10-01T08:00:00Z'}},{'id':'v-fin-1','type':'visit.finish','ref':'v-start-1','payload':{'ended_at':'2026-10-01T08:30:00Z'}})
 assert [x['status'] for x in r['results']]==['applied','applied'] and r['accepted']==2
 assert sync(h,{'id':'v-start-1','type':'visit.start','payload':{'customer_id':c['id']}})['results'][0]['status']=='duplicate'
 assert client.get('/api/visits/today',headers=h).status_code==200
def test_finish_without_known_ref_is_retry_and_not_stored():
 h=H();r=sync(h,{'id':'v-fin-x','type':'visit.finish','ref':'missing'})
 assert r['results'][0]['status']=='retry'
 r=sync(h,{'id':'v-fin-x','type':'visit.finish','ref':'missing'});assert r['results'][0]['status']=='retry'
def test_order_and_payment_events_apply_to_models():
 h=H();c,p,w=base(h,'S2')
 r=sync(h,{'id':'o1','type':'order.create','payload':{'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}})
 assert r['results'][0]['status']=='applied' and r['results'][0]['result_id']
 assert any(o['id']==r['results'][0]['result_id'] for o in client.get('/api/orders',headers=h).json())
 bad=sync(h,{'id':'o2','type':'order.create','payload':{'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':999}]}})
 assert bad['results'][0]['status']=='rejected'
 assert sync(h,{'id':'o2','type':'order.create','payload':{}})['results'][0]['status']=='duplicate'
def test_unknown_type_and_invalid_payload_rejected():
 h=H()
 assert sync(h,{'id':'u1','type':'bogus'})['results'][0]['status']=='rejected'
 assert sync(h,{'id':'u2','type':'order.create','payload':{'customer_id':'x'}})['results'][0]['status']=='rejected'
def test_delivery_events_apply_and_are_idempotent():
 h=H();c,p,w=base(h,'S3')
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':3}]}).json()
 client.post(f"/api/orders/{o['id']}/approve",headers=h)
 d=client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':1}).json()
 r=sync(h,{'id':'d1','type':'delivery.start','entity_id':d['id']},{'id':'d2','type':'delivery.delivered','entity_id':d['id'],'payload':{'status':'delivered','signature':'ok'}})
 assert [x['status'] for x in r['results']]==['applied','applied']
 st=next(x for x in client.get('/api/stock',headers=h).json() if x['product_id']==p['id']);assert st['quantity']==17 and st['reserved']==0
 assert sync(h,{'id':'d2','type':'delivery.delivered','entity_id':d['id']})['results'][0]['status']=='duplicate'
def test_permission_enforced_in_sync():
 h=H();rl=client.post('/api/roles',headers=h,json={'name':'ro-sync','permissions':['crm.read']}).json()
 client.post('/api/users',headers=h,json={'branch_id':1,'username':'rosync','password':'Ro-pass-1','name':'r','role_id':rl['id'],'company_ids':[1]})
 t=client.post('/api/auth/login',json={'username':'rosync','password':'Ro-pass-1'}).json()['token']
 r=sync({'Authorization':'Bearer '+t},{'id':'p1','type':'payment.create','payload':{'customer_id':1,'amount':5,'kind':'receipt'}})
 assert r['results'][0]['status']=='rejected'
