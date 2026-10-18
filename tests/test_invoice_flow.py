import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_invflow.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app, set_invoice_status, Invoice
from fastapi import HTTPException
import pytest
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def test_transition_table():
 i=Invoice(status='cancelled')
 with pytest.raises(HTTPException): set_invoice_status(i,'paid')
 i=Invoice(status='open'); set_invoice_status(i,'partial'); set_invoice_status(i,'paid'); assert i.status=='paid'
 with pytest.raises(HTTPException): set_invoice_status(i,'cancelled')
def test_payment_flow_and_cancelled_rejects():
 h=H()
 c=client.post('/api/customers',headers=h,json={'code':'IF1','name':'f','credit_limit':10**7}).json()
 p=client.post('/api/products',headers=h,json={'sku':'IF1','name':'f','base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json()
 client.post(f"/api/orders/{o['id']}/approve",headers=h)
 inv=next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
 st=lambda: next(i for i in client.get('/api/invoices',headers=h).json() if i['id']==inv['id'])
 pay=lambda a,k='receipt': client.post('/api/payments',headers=h,json={'customer_id':c['id'],'invoice_id':inv['id'],'amount':a,'kind':k})
 assert pay(50).status_code==200 and st()['status']=='partial'
 assert pay(150).status_code==200 and st()['status']=='paid'
 assert pay(1).status_code==400
 assert pay(60,'refund').status_code==200 and st()['status']=='partial' and float(st()['paid'])==140
 assert pay(500,'refund').status_code==400
 assert pay(140,'refund').status_code==200 and st()['status']=='open'
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=h).status_code==200 and st()['status']=='cancelled'
 assert pay(10).status_code==409
