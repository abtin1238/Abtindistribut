import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19tre.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def bal(h,kind,pid):
 return Decimal(str(next(x for x in client.get(f'/api/{kind}s',headers=h).json() if x['id']==pid).get('balance',0)))

def test_endorse_received_check_reduces_supplier_debt():
 h=H(); sid=client.post('/api/suppliers',headers=h,json={'name':'S19'}).json()['id']
 chk=client.post('/api/checks',headers=h,json={'number':'E1','kind':'received','amount':500,'due_date':str(date.today())}).json()['id']
 assert client.patch(f'/api/checks/{chk}',headers=h,json={'status':'endorsed'}).status_code==400
 assert client.post(f'/api/checks/{chk}/endorse',headers=h,json={'supplier_id':999999}).status_code==404
 r=client.post(f'/api/checks/{chk}/endorse',headers=h,json={'supplier_id':sid}); assert r.status_code==200 and r.json()['status']=='endorsed'
 assert client.post(f'/api/checks/{chk}/endorse',headers=h,json={'supplier_id':sid}).status_code==409
 assert client.patch(f'/api/checks/{chk}',headers=h,json={'status':'cleared'}).status_code==409

def test_issued_check_cannot_be_endorsed():
 h=H(); sid=client.post('/api/suppliers',headers=h,json={'name':'S19b'}).json()['id']
 chk=client.post('/api/checks',headers=h,json={'number':'I1','kind':'issued','amount':50,'due_date':str(date.today())}).json()['id']
 assert client.post(f'/api/checks/{chk}/endorse',headers=h,json={'supplier_id':sid}).status_code==400

def test_purchase_return_flow():
 h=H(); sid=client.post('/api/suppliers',headers=h,json={'name':'S19c'}).json()['id']
 wid=client.get('/api/warehouses',headers=h).json()[0]['id']
 pid=client.post('/api/products',headers=h,json={'sku':'PR19','name':'pr'}).json()['id']
 po=client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':wid,'items':[{'product_id':pid,'quantity':10,'unit_cost':100}]}); assert po.status_code==200,po.text; poid=po.json()['id']
 assert client.post(f'/api/purchases/{poid}/return',headers=h,json={'items':[{'product_id':pid,'quantity':1}]}).status_code==409
 assert client.post(f'/api/purchases/{poid}/receive',headers=h).status_code==200
 d=client.get(f'/api/purchases/{poid}',headers=h).json(); assert d['items'][0]['product']=='pr'
 r=client.post(f'/api/purchases/{poid}/return',headers=h,json={'items':[{'product_id':pid,'quantity':4}]}); assert r.status_code==200,r.text
 assert Decimal(r.json()['total'])==Decimal('400.00')
 assert client.post(f'/api/purchases/{poid}/return',headers=h,json={'items':[{'product_id':pid,'quantity':7}]}).status_code==400
 st=[x for x in client.get('/api/stock',headers=h).json() if x['product_id']==pid][0]; assert Decimal(str(st['quantity']))==Decimal('6')
