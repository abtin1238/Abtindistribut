import os,io
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_finrep.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_finrep.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def sale(h,tag,q=3):
 c=client.post('/api/customers',headers=h,json={'code':tag,'name':tag,'credit_limit':10**8}).json()
 p=client.post('/api/products',headers=h,json={'sku':tag,'name':tag,'base_price':100}).json()
 w=client.get('/api/warehouses',headers=h).json()[0]
 client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 o=client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=h).status_code==200
 return c,o,next(i for i in client.get('/api/invoices',headers=h).json() if i['order_id']==o['id'])
def test_profit_loss_and_balance_sheet():
 h=H();sale(h,'F1')
 pl=client.get('/api/reports/profit-loss',headers=h).json();assert float(pl['revenue'])>=300 and float(pl['net_profit'])==float(pl['revenue'])-float(pl['expense'])
 bs=client.get('/api/reports/balance-sheet',headers=h).json();assert bs['balanced'] is True
 assert client.get('/api/reports/profit-loss?start=2030-01-01&end=2020-01-01',headers=h).status_code==400
def test_aging_buckets_and_unallocated():
 h=H();c,o,inv=sale(h,'F2')
 assert client.post('/api/payments',headers=h,json={'customer_id':c['id'],'amount':50,'kind':'receipt'}).status_code==200
 a=client.get('/api/reports/aging',headers=h).json();row=next(x for x in a['rows'] if x['customer_id']==c['id'])
 assert float(row['b0_30'])==300 and float(row['ledger_balance'])==250 and float(row['unallocated'])==-50
 a=client.get('/api/reports/aging?as_of=2099-01-01',headers=h).json();row=next(x for x in a['rows'] if x['customer_id']==c['id']);assert float(row['b90p'])==300
def test_general_ledger_running_balance():
 h=H();c,o,inv=sale(h,'F3',2)
 g=client.get('/api/reports/general-ledger?account_code=1210',headers=h).json();assert g['rows'] and float(g['closing'])==float(g['rows'][-1]['balance'])
 assert client.get('/api/reports/general-ledger?account_code=0000',headers=h).status_code==404
def test_xlsx_exports():
 h=H();sale(h,'F4')
 for u in ('/api/reports/trial-balance.xlsx','/api/reports/aging.xlsx','/api/reports/profit-loss.xlsx','/api/reports/general-ledger.xlsx?account_code=1210'):
  r=client.get(u,headers=h);assert r.status_code==200 and r.content[:2]==b'PK',u
