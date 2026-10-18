import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_ledger.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_ledger.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def setup(h,tag):
 c=client.post('/api/customers',headers=h,json={'code':tag,'name':tag,'credit_limit':10**8}).json()
 p=client.post('/api/products',headers=h,json={'sku':tag,'name':tag,'base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 return c,p,w
def bal(h,cid): return float(next(x for x in client.get('/api/customers',headers=h).json() if x['id']==cid)['balance'])
def tb(h): return client.get('/api/reports/trial-balance',headers=h).json()
def sell(h,c,p,w,q=2):
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 return o,next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
def test_invoice_posts_balanced_entry_and_balance_derived():
 h=H();c,p,w=setup(h,'L1');o,inv=sell(h,c,p,w)
 assert bal(h,c['id'])==float(inv['total'])==200
 t=tb(h);assert t['balanced'] and t['total_debit']==t['total_credit']>0
 lg=client.get(f"/api/customers/{c['id']}/ledger",headers=h).json();assert lg['balance']==200 and lg['rows'][-1]['balance']==200
def test_payment_and_cancel_reverse():
 h=H();c,p,w=setup(h,'L2');o,inv=sell(h,c,p,w)
 assert client.post('/api/payments',headers=h,json={'invoice_id':inv['id'],'amount':50,'kind':'receipt'}).status_code==200
 assert bal(h,c['id'])==150
 assert client.post('/api/payments',headers=h,json={'invoice_id':inv['id'],'amount':50,'kind':'refund'}).status_code==200
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=h).status_code==200
 assert bal(h,c['id'])==0 and tb(h)['balanced']
def test_manual_journal_validation_and_reverse():
 h=H()
 bad={'description':'x','lines':[{'account_code':'1110','debit':100},{'account_code':'4110','credit':90}]}
 assert client.post('/api/journal',headers=h,json=bad).status_code==400
 assert client.post('/api/journal',headers=h,json={'description':'x','lines':[{'account_code':'9999','debit':5},{'account_code':'4110','credit':5}]}).status_code==400
 ok={'description':'m','lines':[{'account_code':'1110','debit':100},{'account_code':'4110','credit':100}]}
 e=client.post('/api/journal',headers=h,json=ok);assert e.status_code==200
 e=e.json();assert len(e['lines'])==2
 rv=client.post(f"/api/journal/{e['id']}/reverse",headers=h);assert rv.status_code==200
 assert client.post(f"/api/journal/{e['id']}/reverse",headers=h).status_code==409
 assert tb(h)['balanced']
def test_auto_entry_cannot_be_reversed_manually():
 h=H();c,p,w=setup(h,'L3');sell(h,c,p,w)
 auto=next(e for e in client.get('/api/journal',headers=h).json() if e['source_type']=='invoice')
 assert client.post(f"/api/journal/{auto['id']}/reverse",headers=h).status_code==409
def test_purchase_receipt_and_supplier_balance():
 h=H();c,p,w=setup(h,'L4')
 s=client.post('/api/suppliers',headers=h,json={'name':'s'}).json()
 pur=client.post('/api/purchases',headers=h,json={'supplier_id':s['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':4,'unit_cost':25}]}).json()
 assert client.post(f"/api/purchases/{pur['id']}/receive",headers=h).status_code==200
 sb=lambda: float(next(x for x in client.get('/api/suppliers',headers=h).json() if x['id']==s['id'])['balance'])
 assert sb()==100
 assert client.post('/api/payments',headers=h,json={'supplier_id':s['id'],'amount':40,'kind':'payment','method':'bank'}).status_code==200
 assert sb()==60 and tb(h)['balanced']
def test_check_lifecycle_posts_entries():
 h=H();c,p,w=setup(h,'L5');o,inv=sell(h,c,p,w)
 ck=client.post('/api/checks',headers=h,json={'number':'K1','amount':120,'due_date':'2026-12-01','customer_id':c['id']}).json()
 assert bal(h,c['id'])==80
 assert client.patch(f"/api/checks/{ck['id']}",headers=h,json={'status':'deposited'}).status_code==200
 assert client.patch(f"/api/checks/{ck['id']}",headers=h,json={'status':'bounced'}).status_code==200
 assert bal(h,c['id'])==200
 assert client.patch(f"/api/checks/{ck['id']}",headers=h,json={'status':'cleared'}).status_code==409
 assert tb(h)['balanced']
def test_credit_limit_uses_ledger_balance():
 h=H();c=client.post('/api/customers',headers=h,json={'code':'L6','name':'x','credit_limit':250}).json()
 p=client.post('/api/products',headers=h,json={'sku':'L6','name':'x','base_price':100}).json();w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 sell(h,c,p,w,2)
 mk=lambda q: client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q}]})
 assert mk(0.4).status_code==200
 assert mk(1).status_code==400
