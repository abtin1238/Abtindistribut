import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_complete.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_complete.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def auth():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_full_distribution_cycle():
 h=auth()
 # organization hierarchy + membership
 r=client.post('/api/organizations/company',headers=h,json={'name':'شرکت تابعه','code':'SUB-01'}); assert r.status_code==200
 sub=r.json()['id']
 me=client.get('/api/me',headers=h).json(); assert {x['id'] for x in me['companies']}=={1,sub}
 # master data
 cust=client.post('/api/customers',headers=h,json={'code':'C-1','name':'مشتری تست','credit_limit':1000000}).json()
 prod=client.post('/api/products',headers=h,json={'sku':'SKU-1','name':'کالای تست','base_price':100}).json()
 wh=client.get('/api/warehouses',headers=h).json()[0]
 assert client.post('/api/stock/adjust',headers=h,json={'warehouse_id':wh['id'],'product_id':prod['id'],'quantity':20,'kind':'in'}).status_code==200
 # purchase -> receive
 sup=client.post('/api/suppliers',headers=h,json={'name':'تامین کننده'}).json()
 pur=client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':wh['id'],'items':[{'product_id':prod['id'],'quantity':5,'unit_cost':50}]}).json()
 assert client.post(f"/api/purchases/{pur['id']}/receive",headers=h).status_code==200
 # order -> approve -> delivery -> stock out
 order=client.post('/api/orders',headers=h,json={'customer_id':cust['id'],'warehouse_id':wh['id'],'items':[{'product_id':prod['id'],'quantity':3}]}).json()
 assert client.post(f"/api/orders/{order['id']}/approve",headers=h).status_code==200
 delivery=client.post(f"/api/orders/{order['id']}/assign-delivery",headers=h,json={'order_id':order['id'],'driver_id':1}).json()
 assert client.patch(f"/api/deliveries/{delivery['id']}",headers=h,json={'status':'delivered','lat':35.7,'lng':51.4,'signature':'ok'}).status_code==200
 # invoice payment
 inv=client.get('/api/invoices',headers=h).json()[0]
 assert client.post('/api/payments',headers=h,json={'customer_id':cust['id'],'invoice_id':inv['id'],'amount':100,'kind':'receipt'}).status_code==200
 # check, visit plan, visit, notification
 assert client.post('/api/checks',headers=h,json={'number':'CHK1','amount':500,'due_date':'2026-12-01'}).status_code==200
 plan=client.post('/api/visit-plans',headers=h,json={'user_id':1,'day':'2026-10-03','customer_ids':[cust['id']]}).json()
 visit=client.post('/api/visits',headers=h,json={'customer_id':cust['id'],'plan_id':plan['id'],'lat':35.7,'lng':51.4}).json()
 assert client.post(f"/api/visits/{visit['id']}/finish",headers=h).status_code==200
 assert client.post('/api/sync',headers=h,json={'events':[{'id':'evt-1','type':'visit.finish','entity_id':visit['id']}]}).json()['accepted']==1
 assert client.post('/api/sync',headers=h,json={'events':[{'id':'evt-1','type':'visit.finish','entity_id':visit['id']}]}).json()['results'][0]['status']=='duplicate'
 assert client.get('/api/dashboard',headers=h).status_code==200
