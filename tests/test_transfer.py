import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_transfer.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def qty(h,pid,wid):
 return float(next((x['quantity'] for x in client.get('/api/stock',headers=h).json() if x['product_id']==pid and x['warehouse_id']==wid),0))
def test_two_step_transfer():
 h=H();w1=client.get('/api/warehouses',headers=h).json()[0]
 w2=client.post('/api/warehouses',headers=h,json={'company_id':1,'name':'انبار دوم'}).json()
 p=client.post('/api/products',headers=h,json={'sku':'TR1','name':'t','base_price':1}).json()
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w1['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 body={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'product_id':p['id'],'quantity':4}
 t=client.post('/api/stock/transfers',headers=h,json=body).json()
 assert qty(h,p['id'],w1['id'])==6 and qty(h,p['id'],w2['id'])==0
 assert client.post(f"/api/stock/transfers/{t['id']}/receive",headers=h).status_code==200
 assert qty(h,p['id'],w2['id'])==4
 assert client.post(f"/api/stock/transfers/{t['id']}/receive",headers=h).status_code==409
 assert client.post('/api/stock/transfers',headers=h,json={**body,'quantity':100}).status_code==400
 t2=client.post('/api/stock/transfers',headers=h,json=body).json()
 assert client.post(f"/api/stock/transfers/{t2['id']}/cancel",headers=h).status_code==200 and qty(h,p['id'],w1['id'])==2+4
