import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_tax.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def test_invoice_tax_and_shipping_and_cancel():
 h=H()
 assert client.put('/api/settings/tax',headers=h,json={'vat_percent':10}).status_code==200
 c=client.post('/api/customers',headers=h,json={'code':'TX1','name':'t','credit_limit':10**7}).json()
 p=client.post('/api/products',headers=h,json={'sku':'TX1','name':'t','base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}],'shipping':20}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 inv=next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
 assert float(inv['subtotal'])==200 and float(inv['tax'])==20 and float(inv['shipping'])==20 and float(inv['total'])==240
 bal=lambda: float(next(x for x in client.get('/api/customers',headers=h).json() if x['id']==c['id'])['balance'])
 assert bal()==240
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=h).status_code==200 and bal()==0
 client.put('/api/settings/tax',headers=h,json={'vat_percent':0})
