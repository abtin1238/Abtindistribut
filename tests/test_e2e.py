import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_e2e.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def ok(r,code=200):
 assert r.status_code==code,r.text;return r.json()
def tb(h): return ok(client.get('/api/reports/trial-balance',headers=h))
def acct(h,code): return next((x for x in tb(h)['rows'] if x['code']==code),{'debit':0,'credit':0})
def test_full_cycle_purchase_sale_partial_delivery_payment_reports():
 h=H();t=uuid.uuid4().hex[:6];me=ok(client.get('/api/me',headers=h))
 sup=ok(client.post('/api/suppliers',headers=h,json={'name':'تأمین '+t}))
 c=ok(client.post('/api/customers',headers=h,json={'code':'E'+t,'name':'مشتری '+t,'credit_limit':10**7}))
 p=ok(client.post('/api/products',headers=h,json={'sku':'E'+t,'name':'کالا','base_price':200,'min_stock':5}))
 w=ok(client.post('/api/warehouses',headers=h,json={'company_id':me['company']['id'],'name':'W'+t}))
 pu=ok(client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':20,'unit_cost':120}]}))
 ok(client.post(f"/api/purchases/{pu['id']}/receive",headers=h))
 assert client.post(f"/api/purchases/{pu['id']}/receive",headers=h).status_code==400
 s=next(x for x in ok(client.get('/api/stock',headers=h)) if x['product_id']==p['id']);assert float(s['quantity'])==20
 assert float(next(x for x in ok(client.get('/api/suppliers',headers=h)) if x['id']==sup['id'])['balance'])!=0
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':10}]}))
 ok(client.post(f"/api/orders/{o['id']}/approve",headers=h))
 s=next(x for x in ok(client.get('/api/stock',headers=h)) if x['product_id']==p['id']);assert float(s['reserved'])==10
 inv=next(i for i in ok(client.get('/api/invoices',headers=h)) if i['order_id']==o['id']);total=float(inv['total'])
 cb=lambda:float(next(x for x in ok(client.get('/api/customers',headers=h)) if x['id']==c['id'])['balance'])
 assert cb()==total
 d=ok(client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':me['user']['id']}))
 ok(client.patch(f"/api/deliveries/{d['id']}",headers=h,json={'status':'delivered','reason':'کسری','items':[{'product_id':p['id'],'quantity':8}]}))
 s=next(x for x in ok(client.get('/api/stock',headers=h)) if x['product_id']==p['id']);assert float(s['quantity'])==12 and float(s['reserved'])==0
 assert cb()<total
 rem=cb();assert rem>0
 ok(client.post('/api/payments',headers=h,json={'customer_id':c['id'],'invoice_id':inv['id'],'amount':rem/2,'kind':'receipt','method':'cash'}))
 assert abs(cb()-rem/2)<0.01
 assert client.post('/api/payments',headers=h,json={'customer_id':c['id'],'invoice_id':inv['id'],'amount':rem*10,'kind':'receipt'}).status_code==400
 ok(client.post('/api/payments',headers=h,json={'customer_id':c['id'],'invoice_id':inv['id'],'amount':cb(),'kind':'receipt','method':'bank'}))
 assert cb()==0
 assert next(i for i in ok(client.get('/api/invoices',headers=h)) if i['id']==inv['id'])['status']=='paid'
 T=tb(h);assert T['balanced'] and float(T['total_debit'])==float(T['total_credit'])
 led=ok(client.get(f"/api/customers/{c['id']}/ledger",headers=h));assert float(led['balance'])==0 and len(led['rows'])>=3
 for u in ('/api/reports/profit-loss','/api/reports/balance-sheet','/api/reports/aging','/api/reports/sales','/api/reports/stock','/api/reports/delivery','/api/dashboard'): ok(client.get(u,headers=h))
 assert ok(client.get('/api/reports/balance-sheet',headers=h))
