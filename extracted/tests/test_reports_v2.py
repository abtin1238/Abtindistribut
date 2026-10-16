import os,time
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_reports_v2.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_reports_v2.sqlite3')
except FileNotFoundError: pass
from decimal import Decimal as D
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r): assert r.status_code==200,r.text;return r.json()
def seed(h,tag,qty=100,price=100,sell=3,disc=0):
 c=ok(client.post('/api/customers',headers=h,json={'code':tag,'name':'مشتری '+tag,'region':'R'+tag,'credit_limit':10**9}))
 p=ok(client.post('/api/products',headers=h,json={'sku':tag,'name':'کالا '+tag,'base_price':price,'min_stock':5}))
 w=client.get('/api/warehouses',headers=h).json()[0]
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':qty,'kind':'in'}))
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':sell,'discount':disc}]}))
 ok(client.post(f"/api/orders/{o['id']}/approve",headers=h));return c,p,w,o
def test_catalog_and_sales_by_every_basis():
 h=H();c,p,w,o=seed(h,'RA',sell=3,disc=20)
 assert {x['name'] for x in ok(client.get('/api/reports/catalog',headers=h))['reports']}>={'sales','customers','inventory','visitors','drivers','profit','aging','finance'}
 for by in ('product','customer','seller','region','branch','day','category'):
  t=ok(client.get('/api/reports/run/sales?by='+by,headers=h));assert t['columns'] and t['rows'],by
  assert sum(D(str(x['net'])) for x in t['rows'])==D(str(t['summary'][3][1]))
 t=ok(client.get('/api/reports/run/sales?by=product',headers=h));r=next(x for x in t['rows'] if x['_key']==str(p['id']))
 assert D(str(r['gross']))==300 and D(str(r['discount']))==20 and D(str(r['net']))==280
 d=ok(client.get(f"/api/reports/sales/detail?by=product&key={p['id']}",headers=h));assert d['rows'][0]['number']==o['number'] and D(str(d['rows'][0]['net']))==280
 assert client.get('/api/reports/run/sales?by=bogus',headers=h).status_code==400
def test_filters_jalali_dates_region_and_range_validation():
 h=H();seed(h,'RB')
 assert ok(client.get('/api/reports/run/sales?by=customer&region=RRB',headers=h))['rows']
 assert ok(client.get('/api/reports/run/sales?by=customer&region=NOPE',headers=h))['rows']==[]
 assert ok(client.get('/api/reports/run/sales?by=day&jstart=1300/01/01&jend=1300/12/29',headers=h))['rows']==[]
 assert client.get('/api/reports/run/sales?jstart=1405/13/01',headers=h).status_code==400
 assert client.get('/api/reports/run/sales?start=2026-02-01&end=2026-01-01',headers=h).status_code==400
def test_customers_inventory_reports():
 h=H();c,p,w,o=seed(h,'RC',qty=4)
 t=ok(client.get('/api/reports/run/customers',headers=h));assert any(x['code']=='RC' and x['orders']==1 for x in t['rows'])
 low=ok(client.get('/api/reports/run/inventory?kind=low',headers=h));assert any(x['_key']==str(p['id']) for x in low['rows'])
 st=ok(client.get('/api/reports/run/inventory?kind=stock',headers=h));assert st['rows']
 mv=ok(client.get('/api/reports/run/inventory?kind=movement',headers=h));assert any(x['_key']==str(p['id']) and D(str(x['in_qty']))==4 for x in mv['rows'])
 assert client.get('/api/reports/run/inventory?kind=bogus',headers=h).status_code==400
def test_visitor_driver_finance_profit_aging_run():
 h=H()
 for n in ('visitors','drivers','finance','profit','aging'): assert 'rows' in ok(client.get('/api/reports/run/'+n,headers=h)),n
 assert client.get('/api/reports/run/nope',headers=h).status_code==404
def test_sync_export_xlsx_and_pdf_errors_are_clean():
 h=H();seed(h,'RD')
 r=client.get('/api/reports/run/sales/export?format=xlsx&by=product',headers=h);assert r.status_code==200 and r.content[:2]==b'PK'
 r=client.get('/api/reports/run/sales/export?format=pdf&by=product',headers=h);assert r.status_code in (200,501),r.text
 assert client.get('/api/reports/run/sales/export?format=exe',headers=h).status_code==422
def test_background_job_lifecycle_and_isolation():
 h=H();seed(h,'RE')
 j=ok(client.post('/api/reports/jobs',headers=h,json={'report':'sales','format':'xlsx','params':{'by':'customer'}}))
 for _ in range(50):
  j=ok(client.get(f"/api/reports/jobs/{j['id']}",headers=h))
  if j['status'] in ('done','failed'): break
  time.sleep(.1)
 assert j['status']=='done' and 'path' not in j,j
 r=client.get(f"/api/reports/jobs/{j['id']}/download",headers=h);assert r.status_code==200 and r.content[:2]==b'PK'
 assert any(x['id']==j['id'] for x in ok(client.get('/api/reports/jobs',headers=h)))
 assert client.post('/api/reports/jobs',headers=h,json={'report':'sales','params':{'jstart':'bad'}}).status_code==400
 assert client.post('/api/reports/jobs',headers=h,json={'report':'nope'}).status_code==404
 assert client.get(f"/api/reports/jobs/{j['id']}/download").status_code==401
def test_ceo_summary_drilldown_holding_and_reconcile():
 h=H();c,p,w,o=seed(h,'RF',sell=2)
 s=ok(client.get('/api/ceo/summary',headers=h));k=s['kpis']
 assert D(str(k['sales_today']['value']))>=200 and k['sales_today']['drill']['report']=='sales'
 for key in ('receivables','cash','stock_value','liquidity','checks','gross_profit_month'): assert key in k,key
 # drill-down: عدد کارت = جمع گزارش مربوط
 d=k['sales_month']['drill'];rep=ok(client.get('/api/reports/run/'+d['report'],headers=h,params=d['params']))
 assert D(str(rep['summary'][3][1]))==D(str(k['sales_month']['value']))
 ho=ok(client.get('/api/ceo/holding',headers=h));assert ho['companies'] and ho['warnings'] and 'sales_month' in ho['consolidated']
 assert sum(D(str(x['kpis']['sales_month']['value'])) for x in ho['companies'])==D(str(ho['consolidated']['sales_month']))
 rc=ok(client.get('/api/ceo/reconcile',headers=h));assert rc['checks'][0]['ok'] is True   # تراز آزمایشی همیشه متوازن
 assert len(ok(client.get('/api/ceo/trend?days=7',headers=h))['series'])==7
def test_non_manager_cannot_see_ceo_or_reports():
 h=H();roles={r['name']:r['id'] for r in ok(client.get('/api/roles',headers=h))}
 ok(client.post('/api/users',headers=h,json={'username':'rpt_seller','password':'Seller#12345','name':'ف','role_id':roles['فروشنده'],'company_ids':[ok(client.get('/api/me',headers=h))['company']['id']]}))
 t=client.post('/api/auth/login',json={'username':'rpt_seller','password':'Seller#12345'});assert t.status_code==200,t.text
 sh={'Authorization':'Bearer '+t.json()['token']}
 assert client.get('/api/ceo/summary',headers=sh).status_code==403
 assert client.get('/api/reports/run/sales',headers=sh).status_code==403
 assert client.post('/api/reports/jobs',headers=sh,json={'report':'sales'}).status_code==403
