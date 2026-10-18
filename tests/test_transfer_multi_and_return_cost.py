import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_transfer_multi.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_transfer_multi.sqlite3')
except FileNotFoundError: pass
from decimal import Decimal as D
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r): assert r.status_code==200,r.text;return r.json()
def qty(h,pid,wid): return D(str(next((x['quantity'] for x in client.get('/api/stock',headers=h).json() if x['product_id']==pid and x['warehouse_id']==wid),0)))
def product(h,pid): return next(x for x in client.get('/api/products',headers=h).json() if x['id']==pid)

def test_multi_item_transfer_receive_cancel():
 h=H();w1=client.get('/api/warehouses',headers=h).json()[0];w2=ok(client.post('/api/warehouses',headers=h,json={'company_id':1,'name':'انبار م۲'}))
 pa=ok(client.post('/api/products',headers=h,json={'sku':'MTA','name':'a','base_price':1}));pb=ok(client.post('/api/products',headers=h,json={'sku':'MTB','name':'b','base_price':1}))
 for p,q in ((pa,10),(pb,5)): ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w1['id'],'product_id':p['id'],'quantity':q,'kind':'in'}))
 body={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'items':[{'product_id':pa['id'],'quantity':4},{'product_id':pb['id'],'quantity':5}]}
 t=ok(client.post('/api/stock/transfers',headers=h,json=body));assert len(t['items'])==2
 assert qty(h,pa['id'],w1['id'])==6 and qty(h,pb['id'],w1['id'])==0 and qty(h,pa['id'],w2['id'])==0
 ok(client.post(f"/api/stock/transfers/{t['id']}/receive",headers=h))
 assert qty(h,pa['id'],w2['id'])==4 and qty(h,pb['id'],w2['id'])==5
 assert client.post(f"/api/stock/transfers/{t['id']}/receive",headers=h).status_code==409
 lst=[x for x in ok(client.get('/api/stock/transfers',headers=h)) if x['id']==t['id']][0];assert lst['items_count']==2
 # لغو: برگشت هر دو قلم به مبدأ
 t2=ok(client.post('/api/stock/transfers',headers=h,json={**body,'items':[{'product_id':pa['id'],'quantity':6}]}))
 ok(client.post(f"/api/stock/transfers/{t2['id']}/cancel",headers=h));assert qty(h,pa['id'],w1['id'])==6

def test_multi_item_transfer_is_atomic_and_legacy_body_works():
 h=H();w1=client.get('/api/warehouses',headers=h).json()[0];w2=client.get('/api/warehouses',headers=h).json()[1]
 pa=ok(client.post('/api/products',headers=h,json={'sku':'MTC','name':'c','base_price':1}));pb=ok(client.post('/api/products',headers=h,json={'sku':'MTD','name':'d','base_price':1}))
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w1['id'],'product_id':pa['id'],'quantity':10,'kind':'in'}))
 bad={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'items':[{'product_id':pa['id'],'quantity':3},{'product_id':pb['id'],'quantity':1}]}
 assert client.post('/api/stock/transfers',headers=h,json=bad).status_code==400 and qty(h,pa['id'],w1['id'])==10   # قلم دوم موجودی ندارد ⇒ هیچ‌چیز کم نمی‌شود
 assert client.post('/api/stock/transfers',headers=h,json={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'items':[]}).status_code==422
 dup={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'items':[{'product_id':pa['id'],'quantity':2},{'product_id':pa['id'],'quantity':3}]}
 t=ok(client.post('/api/stock/transfers',headers=h,json=dup));assert len(t['items'])==1 and D(str(t['items'][0]['quantity']))==5   # تکراری جمع می‌شود
 old={'from_warehouse_id':w1['id'],'to_warehouse_id':w2['id'],'product_id':pa['id'],'quantity':1}
 ok(client.post('/api/stock/transfers',headers=h,json=old));assert qty(h,pa['id'],w1['id'])==4

def test_purchase_return_recomputes_average_cost():
 h=H();w=client.get('/api/warehouses',headers=h).json()[0];sup=ok(client.post('/api/suppliers',headers=h,json={'name':'SRC'}))
 p=ok(client.post('/api/products',headers=h,json={'sku':'RC1','name':'rc','base_price':1}))
 def buy(q,c):
  po=ok(client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q,'unit_cost':c}]}));ok(client.post(f"/api/purchases/{po['id']}/receive",headers=h));return po
 po1=buy(10,100);po2=buy(10,200);assert D(str(product(h,p['id'])['avg_cost']))==D('150')
 ok(client.post(f"/api/purchases/{po2['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':5}]}))
 assert D(str(product(h,p['id'])['avg_cost'])).quantize(D('0.0001'))==D('133.3333')      # (3000−5×200)/15
 ok(client.post(f"/api/purchases/{po1['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':4}]}))
 assert D(str(product(h,p['id'])['avg_cost'])).quantize(D('0.01'))==D('145.45')           # (15×133.3333−4×100)/11

def test_campaign_beats_base_price_and_role_cap():
 h=H();w=client.get('/api/warehouses',headers=h).json()[0]
 p=ok(client.post('/api/products',headers=h,json={'sku':'CMP1','name':'cmp','base_price':1000}))
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'}))
 ok(client.post('/api/campaigns',headers=h,json={'name':'حراج','product_id':p['id'],'discount_percent':20,'min_qty':2}))
 q1=ok(client.get(f"/api/pricing/quote?product_id={p['id']}&quantity=1",headers=h));assert D(q1['unit_price'])==D('1000')
 q2=ok(client.get(f"/api/pricing/quote?product_id={p['id']}&quantity=2",headers=h));assert D(q2['unit_price'])==D('800') and 'کمپین' in q2['reason']

def test_units_and_barcode():
 h=H();w=client.get('/api/warehouses',headers=h).json()[0]
 p=ok(client.post('/api/products',headers=h,json={'sku':'UN1','name':'un','base_price':10,'barcode':'6260001'}))
 assert client.post('/api/products',headers=h,json={'sku':'UN2','name':'un2','barcode':'6260001'}).status_code==409
 ok(client.post(f"/api/products/{p['id']}/units",headers=h,json={'unit':'کارتن','factor':12,'barcode':'6260002'}))
 assert ok(client.get('/api/products/by-barcode/6260002',headers=h))['factor'] in (12,'12','12.0000',12.0)
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':100,'kind':'in'}))
 w2=ok(client.post('/api/warehouses',headers=h,json={'company_id':1,'name':'انبار واحد'}))
 ok(client.post('/api/stock/transfers',headers=h,json={'from_warehouse_id':w['id'],'to_warehouse_id':w2['id'],'items':[{'product_id':p['id'],'quantity':2,'unit':'کارتن'}]}))
 assert qty(h,p['id'],w['id'])==76
 assert client.post('/api/stock/transfers',headers=h,json={'from_warehouse_id':w['id'],'to_warehouse_id':w2['id'],'items':[{'product_id':p['id'],'quantity':1,'unit':'پالت'}]}).status_code==400
