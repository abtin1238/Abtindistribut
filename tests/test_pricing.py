import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_pricing.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def login(u='admin',p='test-password'):
 r=client.post('/api/auth/login',json={'username':u,'password':p}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def test_group_price_and_discount_permission():
 H=login()
 c=client.post('/api/customers',headers=H,json={'code':'PG1','name':'g','customer_group':'vip','credit_limit':1000000}).json()
 p=client.post('/api/products',headers=H,json={'sku':'PG1','name':'p','base_price':100}).json()
 w=client.get('/api/warehouses',headers=H).json()[0]
 client.post('/api/stock/adjust',headers=H,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':20,'kind':'in'})
 assert client.post('/api/price-rules',headers=H,json={'product_id':p['id'],'customer_group':'vip','discount_percent':20}).status_code==200
 assert client.post('/api/price-rules',headers=H,json={'product_id':p['id'],'customer_group':'other','price':1}).status_code==200
 o=client.post('/api/orders',headers=H,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json()
 assert float(o['total'])==160
 role=next(x['id'] for x in client.get('/api/roles/templates',headers=H,params={}).json() if x['name']=='فروشنده') if False else next(x['id'] for x in client.post('/api/roles/templates',headers=H).json() if x['name']=='فروشنده')
 assert client.post('/api/users',headers=H,json={'username':'seller9','password':'Sell-pass-1','name':'s','role_id':role,'company_ids':[1]}).status_code==200
 S=login('seller9','Sell-pass-1')
 body={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1,'discount':50}]}
 assert client.post('/api/orders',headers=S,json=body).status_code==403
