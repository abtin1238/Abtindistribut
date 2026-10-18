import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19cat.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_brand_category_product_patch_flow():
 h=H()
 b=client.post('/api/brands',headers=h,json={'name':'B1'}); assert b.status_code==200,b.text; bid=b.json()['id']
 assert client.post('/api/brands',headers=h,json={'name':'B1'}).status_code==409
 c=client.post('/api/categories',headers=h,json={'name':'C1'}).json(); cid=c['id']
 assert client.post('/api/categories',headers=h,json={'name':'C2','parent_id':999999}).status_code==404
 p=client.post('/api/products',headers=h,json={'sku':'S19','name':'x','brand_id':bid,'category_id':cid}); assert p.status_code==200,p.text; pid=p.json()['id']
 assert client.post('/api/products',headers=h,json={'sku':'S20','name':'y','brand_id':999999}).status_code==404
 assert client.delete(f'/api/brands/{bid}',headers=h).status_code==409
 assert client.delete(f'/api/categories/{cid}',headers=h).status_code==409
 r=client.patch(f'/api/products/{pid}',headers=h,json={'base_price':5,'brand_id':None,'active':False}); assert r.status_code==200 and r.json()['brand_id'] is None and r.json()['active'] is False
 assert client.patch(f'/api/products/{pid}',headers=h,json={'base_price':-1}).status_code==400
 assert client.delete(f'/api/brands/{bid}',headers=h).status_code==200
