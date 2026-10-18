import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_invdetail.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def test_invoice_lines_and_detail():
 h=H()
 c=client.post('/api/customers',headers=h,json={'code':'ID1','name':'خریدار','credit_limit':10**7}).json()
 p1=client.post('/api/products',headers=h,json={'sku':'ID1','name':'الف','base_price':80}).json()
 p2=client.post('/api/products',headers=h,json={'sku':'ID2','name':'ب','base_price':50}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 for p in (p1,p2): client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p1['id'],'quantity':2},{'product_id':p2['id'],'quantity':1,'discount':10}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 inv=next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
 d=client.get(f"/api/invoices/{inv['id']}",headers=h)
 assert d.status_code==200
 d=d.json()
 assert len(d['lines'])==2 and sorted(float(l['line_total']) for l in d['lines'])==[40,160]
 assert d['customer']['name']=='خریدار' and d['order_number']==o['number'] and float(d['remaining'])==float(inv['total'])
 assert client.get(f"/api/invoices/{inv['id']}").status_code==401
 assert client.get('/api/invoices/999999',headers=h).status_code==404
 assert client.get('/web/invoice.html').status_code==200
