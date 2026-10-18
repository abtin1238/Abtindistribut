import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19price.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_tier_pricing_and_quote_explanation():
 h=H(); pid=client.post('/api/products',headers=h,json={'sku':'PT19','name':'pt','base_price':100}).json()['id']
 assert client.post('/api/price-rules',headers=h,json={'product_id':pid}).status_code==400
 assert client.post('/api/price-rules',headers=h,json={'product_id':pid,'discount_percent':10,'min_qty':10}).status_code==200
 assert client.post('/api/price-rules',headers=h,json={'product_id':pid,'price':70,'min_qty':50}).status_code==200
 q=lambda n: client.get('/api/pricing/quote',headers=h,params={'product_id':pid,'quantity':n}).json()
 assert Decimal(q(1)['unit_price'])==100 and q(1)['rule_id'] is None
 assert Decimal(q(10)['unit_price'])==90 and 'تخفیف' in q(10)['reason']
 assert Decimal(q(50)['unit_price'])==70 and Decimal(q(50)['total'])==3500
 assert client.get('/api/pricing/quote',headers=h,params={'product_id':pid,'quantity':0}).status_code==400

def test_rule_toggle_and_delete():
 h=H(); pid=client.post('/api/products',headers=h,json={'sku':'PT19b','name':'pt','base_price':100}).json()['id']
 rid=client.post('/api/price-rules',headers=h,json={'product_id':pid,'price':50}).json()['id']
 assert client.patch(f'/api/price-rules/{rid}',headers=h,params={'active':False}).json()['active'] is False
 assert Decimal(client.get('/api/pricing/quote',headers=h,params={'product_id':pid,'quantity':1}).json()['unit_price'])==100
 assert client.delete(f'/api/price-rules/{rid}',headers=h).status_code==200
