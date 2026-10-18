import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_reports.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_reports.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def login():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def item(H,sku,min_stock,qty):
 p=client.post('/api/products',headers=H,json={'sku':sku,'name':sku,'base_price':10,'min_stock':min_stock}).json()
 w=client.get('/api/warehouses',headers=H).json()[0]
 assert client.post('/api/stock/adjust',headers=H,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':qty,'kind':'in'}).status_code==200
 return p,w

def test_low_stock_uses_min_stock():
 H=login()
 low,w=item(H,'R-LOW',10,5)    # available 5 <= min 10  -> low
 ok,_=item(H,'R-OK',10,50)     # available 50 > min 10  -> fine
 nomin,_=item(H,'R-NOMIN',0,5) # no min set, available>0 -> fine
 d=client.get('/api/reports/stock',headers=H).json()
 ids={x['product_id'] for x in d['low_stock']}
 assert low['id'] in ids and ok['id'] not in ids and nomin['id'] not in ids
 row=next(x for x in d['low_stock'] if x['product_id']==low['id'])
 assert float(row['shortage'])==5
 # warehouse filter
 assert client.get(f"/api/reports/stock?warehouse_id={w['id']+999}",headers=H).json()['items']==[]

def test_delivery_report_date_filter():
 H=login()
 base=client.get('/api/reports/delivery',headers=H).json()
 assert base['total']==0
 far=client.get('/api/reports/delivery?start=2000-01-01&end=2000-01-02',headers=H).json()
 assert far['total']==0
 assert client.get('/api/reports/delivery?start=2026-02-01&end=2026-01-01',headers=H).status_code==400

def test_sequence_numbers_unique_and_increasing():
 H=login()
 w=client.get('/api/warehouses',headers=H).json()[0]
 c=client.post('/api/customers',headers=H,json={'code':'SQ1','name':'s'}).json()
 p=client.post('/api/products',headers=H,json={'sku':'SQ1','name':'s','base_price':1}).json()
 client.post('/api/stock/adjust',headers=H,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 nums=[client.post('/api/orders',headers=H,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}).json()['number'] for _ in range(3)]
 seq=[int(n.rsplit('-',1)[1]) for n in nums]
 assert len(set(nums))==3 and seq==sorted(seq) and seq[2]-seq[0]==2
