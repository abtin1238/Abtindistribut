import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_returns.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_returns.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def setup(h,tag):
 c=client.post('/api/customers',headers=h,json={'code':tag,'name':tag,'credit_limit':10**8}).json()
 p=client.post('/api/products',headers=h,json={'sku':tag,'name':tag,'base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 return c,p,w
def bal(h,cid): return float(next(x for x in client.get('/api/customers',headers=h).json() if x['id']==cid)['balance'])
def stock(h,pid): return next(x for x in client.get('/api/stock',headers=h).json() if x['product_id']==pid)
def deliver(h,c,p,w,q=4,items=None):
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 d=client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':1}).json()
 body={'status':'delivered'}
 if items is not None: body['items']=items;body['reason']='تحویل ناقص'
 r=client.patch(f"/api/deliveries/{d['id']}",headers=h,json=body);assert r.status_code==200,r.text
 inv=next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
 return o,inv
def test_return_after_delivery():
 h=H();c,p,w=setup(h,'R1');o,inv=deliver(h,c,p,w)
 assert bal(h,c['id'])==400 and stock(h,p['id'])['quantity']==46
 r=client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':1}],'reason':'x'});assert r.status_code==200,r.text
 assert bal(h,c['id'])==300 and stock(h,p['id'])['quantity']==47
 assert client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':4}]}).status_code==400
 assert client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':3}]}).status_code==200
 assert bal(h,c['id'])==0
 i=next(x for x in client.get('/api/invoices',headers=h).json() if x['id']==inv['id']);assert i['status']=='paid' and float(i['returned'])==400
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']
def test_return_requires_delivered_and_overpay_blocked():
 h=H();c,p,w=setup(h,'R2')
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json()
 assert client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':1}]}).status_code==409
 o,inv=deliver(h,c,p,w,2)
 assert client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':1}]}).status_code==200
 assert client.post('/api/payments',headers=h,json={'invoice_id':inv['id'],'amount':150,'kind':'receipt'}).status_code==400
 assert client.post('/api/payments',headers=h,json={'invoice_id':inv['id'],'amount':100,'kind':'receipt'}).status_code==200
def test_partial_delivery_adjusts_invoice_stock_and_ledger():
 h=H();c,p,w=setup(h,'R3');o,inv=deliver(h,c,p,w,5,[{'product_id':p['id'],'quantity':3}])
 s=stock(h,p['id']);assert s['quantity']==47 and s['reserved']==0
 assert bal(h,c['id'])==300
 rs=[x for x in client.get('/api/sales-returns',headers=h).json() if x['order_id']==o['id']];assert len(rs)==1 and rs[0]['restocked'] is False and float(rs[0]['total'])==200
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']
def test_partial_delivery_invalid_qty():
 h=H();c,p,w=setup(h,'R4')
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json()
 client.post(f"/api/orders/{o['id']}/approve",headers=h)
 d=client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':1}).json()
 assert client.patch(f"/api/deliveries/{d['id']}",headers=h,json={'status':'delivered','items':[{'product_id':p['id'],'quantity':9}]}).status_code==400
