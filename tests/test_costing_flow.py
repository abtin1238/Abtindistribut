import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_costing.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_costing.sqlite3')
except FileNotFoundError: pass
from decimal import Decimal as D
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r): assert r.status_code==200,r.text;return r.json()
def money(v): return D(str(v))
def setup(h,tag,price=100):
 c=ok(client.post('/api/customers',headers=h,json={'code':tag,'name':tag,'credit_limit':10**9}))
 p=ok(client.post('/api/products',headers=h,json={'sku':tag,'name':tag,'base_price':price}))
 w=client.get('/api/warehouses',headers=h).json()[0]
 sup=ok(client.post('/api/suppliers',headers=h,json={'name':'S'+tag}))
 return c,p,w,sup
def buy(h,sup,p,w,qty,cost,discount=0,freight=0):
 po=ok(client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'freight':freight,'items':[{'product_id':p['id'],'quantity':qty,'unit_cost':cost,'discount':discount}]}))
 return ok(client.post(f"/api/purchases/{po['id']}/receive",headers=h)),po
def product(h,pid): return next(x for x in client.get('/api/products',headers=h).json() if x['id']==pid)
def tb(h): return client.get('/api/reports/trial-balance',headers=h).json()
def bal(h,code): return money(next((x['balance'] for x in tb(h)['rows'] if x['code']==code),0))
class Snap:
 def __init__(s,h): s.h=h;s.b={x['code']:money(x['balance']) for x in tb(h)['rows']}
 def __call__(s,code): return bal(s.h,code)-s.b.get(code,D(0))
def deliver(h,o,items=None,reason=''):
 u=client.get('/api/me',headers=h).json()['user']['id']
 d=ok(client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':u}))
 body={'status':'delivered','reason':reason}
 if items is not None: body['items']=items
 return ok(client.patch(f"/api/deliveries/{d['id']}",headers=h,json=body))
def sell(h,c,p,w,q,discount=0):
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':q,'discount':discount}]}))
 ok(client.post(f"/api/orders/{o['id']}/approve",headers=h));return o
def test_purchase_discount_freight_and_weighted_average():
 h=H();c,p,w,sup=setup(h,'K1');bal0=Snap(h)
 # ۱۰ عدد × ۱۰۰ − تخفیف ۵۰ + حمل ۱۰۰ = ۱۰۵۰ ← بهای واحد ۱۰۵
 po,raw=buy(h,sup,p,w,10,100,discount=50,freight=100);assert money(raw['total'])==1050
 assert money(product(h,p['id'])['avg_cost'])==D('105')
 # ۱۰ عدد دیگر × ۱۹۵ ← میانگین (۱۰×۱۰۵ + ۱۰×۱۹۵)/۲۰ = ۱۵۰
 buy(h,sup,p,w,10,195);assert money(product(h,p['id'])['avg_cost'])==D('150')
 assert bal0('1310')==D(1050+1950) and tb(h)['balanced']
def test_delivery_posts_cogs_and_profit_report_reconciles():
 h=H();c,p,w,sup=setup(h,'K2',price=200);bal0=Snap(h);buy(h,sup,p,w,20,120)
 o=sell(h,c,p,w,5,discount=50);deliver(h,o)
 assert bal0('5100')==D(600) and bal0('1310')==D(20*120-600) and tb(h)['balanced']
 rep=client.get('/api/reports/profit-loss/breakdown?by=product',headers=h).json();it=next(x for x in rep['items'] if x['key']==p['id'])
 # فروش ناخالص ۱۰۰۰، تخفیف ۵۰، درآمد ۹۵۰، بها ۶۰۰، سود ۳۵۰
 assert (money(it['gross_sales']),money(it['discount']),money(it['revenue']),money(it['cogs']),money(it['profit']))==(D(1000),D(50),D(950),D(600),D(350))
 assert rep['ledger']['cogs_matches_lines'] is True
 pl=client.get('/api/reports/profit-loss',headers=h).json();assert money(pl['cogs'])>=D(600)
def test_partial_delivery_costs_only_delivered_qty():
 h=H();c,p,w,sup=setup(h,'K3');bal0=Snap(h);buy(h,sup,p,w,10,60)
 o=sell(h,c,p,w,4);deliver(h,o,items=[{'product_id':p['id'],'quantity':3}],reason='کسری')
 assert bal0('5100')==D(180) and bal0('1310')==D(10*60-180) and tb(h)['balanced']
def test_return_restocks_at_original_cost_and_reverses_cogs_and_discount():
 h=H();c,p,w,sup=setup(h,'K4',price=100);bal0=Snap(h);buy(h,sup,p,w,10,40)
 o=sell(h,c,p,w,4,discount=40);deliver(h,o)               # فروش ۴×۱۰۰−۴۰=۳۶۰، بها ۱۶۰
 assert bal0('5100')==D(160)
 ok(client.post(f"/api/orders/{o['id']}/return",headers=h,json={'items':[{'product_id':p['id'],'quantity':2}],'reason':'x'}))
 assert bal0('5100')==D(80) and bal0('1310')==D(10*40-80) and tb(h)['balanced']
 assert money(product(h,p['id'])['avg_cost'])==D('40')
 rep=client.get('/api/reports/profit-loss/breakdown?by=product',headers=h).json();it=next(x for x in rep['items'] if x['key']==p['id'])
 assert (money(it['revenue']),money(it['cogs']),money(it['discount']))==(D(180),D(80),D(20))
def test_manual_adjust_uses_average_cost_and_dashboard_value():
 h=H();c,p,w,sup=setup(h,'K5');bal0=Snap(h);buy(h,sup,p,w,5,30)
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':2,'kind':'out','reference':'damage'}))
 assert bal0('5200')==D(60) and bal0('1310')==D(90) and tb(h)['balanced']
 d=client.get('/api/dashboard',headers=h).json();assert d['stock_value'] is not None and d['gross_profit_month'] is not None
def test_invalid_purchase_discount_and_breakdown_params():
 h=H();c,p,w,sup=setup(h,'K6')
 r=client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1,'unit_cost':10,'discount':11}]});assert r.status_code==400
 assert client.get('/api/reports/profit-loss/breakdown?by=zzz',headers=h).status_code==400
