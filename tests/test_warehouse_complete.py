import os,uuid
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_wh_complete.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_wh_complete.sqlite3')
except FileNotFoundError: pass
from datetime import date,timedelta
from decimal import Decimal as D
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r,code=200): assert r.status_code==code,r.text;return r.json()
def setup(h,price=100,**kw):
 t=uuid.uuid4().hex[:6]
 p=ok(client.post('/api/products',headers=h,json={'sku':'W'+t,'name':'k'+t,'base_price':price,**kw}))
 w=client.get('/api/warehouses',headers=h).json()[0];sup=ok(client.post('/api/suppliers',headers=h,json={'name':'S'+t}))
 return p,w,sup
def buy(h,sup,p,w,qty,cost,**it):
 po=ok(client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':qty,'unit_cost':cost,**it}]}))
 return ok(client.post(f"/api/purchases/{po['id']}/receive",headers=h))
def stock(h,p,w): return next(x for x in client.get('/api/stock',headers=h).json() if x['product_id']==p['id'] and x['warehouse_id']==w['id'])
def bal(h,code): return D(str(next((x['balance'] for x in client.get('/api/reports/trial-balance',headers=h).json()['rows'] if x['code']==code),0)))

def test_out_requires_reason_and_moves_record_user_time_reason():
 h=H();p,w,sup=setup(h);buy(h,sup,p,w,10,50)
 base={'warehouse_id':w['id'],'product_id':p['id'],'quantity':2,'kind':'out'}
 assert client.post('/api/stock/adjust',headers=h,json=base).status_code==400
 assert client.post('/api/stock/adjust',headers=h,json={**base,'kind':'zzz','reason':'x'}).status_code==400
 ok(client.post('/api/stock/adjust',headers=h,json={**base,'reason':'شکستگی'}))
 mv=ok(client.get(f"/api/stock/moves?product_id={p['id']}",headers=h))
 m=next(x for x in mv if x['kind']=='out');assert m['reason']=='شکستگی' and m['user'] and m['created_at'] and m['direction']=='out'

def test_kardex_running_balance_matches_stock():
 h=H();p,w,sup=setup(h);buy(h,sup,p,w,10,50)
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':3,'kind':'out','reason':'مصرف'}))
 k=ok(client.get(f"/api/stock/kardex?product_id={p['id']}&warehouse_id={w['id']}",headers=h))
 assert [D(str(r['balance'])) for r in k['rows']]==[10,7] and D(str(k['closing']))==7 and k['matches_stock'] is True
 assert D(str(k['total_in']))==10 and D(str(k['total_out']))==3
 tomorrow=(date.today()+timedelta(days=2)).isoformat()
 k2=ok(client.get(f"/api/stock/kardex?product_id={p['id']}&start={tomorrow}",headers=h));assert D(str(k2['opening']))==7 and k2['rows']==[]
 assert client.get(f"/api/stock/kardex?product_id={p['id']}&start=2030-01-02&end=2030-01-01",headers=h).status_code==400

def test_batches_fefo_expiry_and_report():
 h=H();p,w,sup=setup(h,track_batch=True)
 po=client.post('/api/purchases',headers=h,json={'supplier_id':sup['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':5,'unit_cost':10}]});assert po.status_code==400   # بچ الزامی
 soon=(date.today()+timedelta(days=10)).isoformat();late=(date.today()+timedelta(days=200)).isoformat();gone=(date.today()-timedelta(days=3)).isoformat()
 buy(h,sup,p,w,10,10,batch_no='L-LATE',expiry_date=late);buy(h,sup,p,w,6,10,batch_no='L-SOON',expiry_date=soon);buy(h,sup,p,w,2,10,batch_no='L-OLD',expiry_date=gone)
 bs={b['batch_no']:b for b in ok(client.get(f"/api/stock/batches?product_id={p['id']}",headers=h))}
 assert bs['L-OLD']['status']=='expired' and bs['L-SOON']['status']=='expiring' and bs['L-LATE']['status']=='ok'
 ex=ok(client.get('/api/stock/expiring?days=30',headers=h));mine=[x for x in ex['items'] if x['product_id']==p['id']];assert {x['batch_no'] for x in mine}=={'L-OLD','L-SOON'} and ex['expired_count']>=1
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':3,'kind':'out','reason':'ضایعات'}))   # FEFO: ابتدا منقضی‌شده
 bs={b['batch_no']:D(str(b['quantity'])) for b in ok(client.get(f"/api/stock/batches?product_id={p['id']}&include_empty=true",headers=h))}
 assert bs=={'L-OLD':0,'L-SOON':5,'L-LATE':10},bs
 assert client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':1,'kind':'out','reason':'x','batch_no':'NOPE'}).status_code==400
 assert client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':1,'kind':'in'}).status_code==400   # ورود بچ‌دار بدون شماره بچ

def test_delivery_consumes_batches_fefo():
 h=H();p,w,sup=setup(h,price=100,track_batch=True);c=ok(client.post('/api/customers',headers=h,json={'code':'C'+uuid.uuid4().hex[:5],'name':'c','credit_limit':10**9}))
 buy(h,sup,p,w,5,10,batch_no='B1',expiry_date=(date.today()+timedelta(days=50)).isoformat());buy(h,sup,p,w,5,10,batch_no='B2',expiry_date=(date.today()+timedelta(days=90)).isoformat())
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':7}]}));ok(client.post(f"/api/orders/{o['id']}/approve",headers=h))
 u=client.get('/api/me',headers=h).json()['user']['id'];d=ok(client.post(f"/api/orders/{o['id']}/assign-delivery",headers=h,json={'order_id':o['id'],'driver_id':u}))
 ok(client.patch(f"/api/deliveries/{d['id']}",headers=h,json={'status':'delivered'}))
 bs={b['batch_no']:D(str(b['quantity'])) for b in ok(client.get(f"/api/stock/batches?product_id={p['id']}&include_empty=true",headers=h))}
 assert bs=={'B1':0,'B2':3}

def test_stock_count_flow_adjusts_stock_ledger_and_is_final():
 h=H();p,w,sup=setup(h);buy(h,sup,p,w,10,40);inv0=bal(h,'1310');adj0=bal(h,'5200')
 cnt=ok(client.post('/api/stock/counts',headers=h,json={'warehouse_id':w['id'],'product_ids':[p['id']],'note':'پایان ماه'}))
 assert client.post('/api/stock/counts',headers=h,json={'warehouse_id':w['id']}).status_code==409          # برگه‌ی باز دیگر
 assert client.post(f"/api/stock/counts/{cnt['id']}/approve",headers=h,json={}).status_code==409           # هنوز شمارش نشده
 r=ok(client.put(f"/api/stock/counts/{cnt['id']}/lines",headers=h,json={'lines':[{'product_id':p['id'],'counted_qty':7}]}))
 assert r['status']=='counting' and D(str(r['lines'][0]['difference']))==-3 and D(str(r['total_value_difference']))==-120
 assert client.put(f"/api/stock/counts/{cnt['id']}/lines",headers=h,json={'lines':[{'product_id':999999,'counted_qty':1}]}).status_code==400
 a=ok(client.post(f"/api/stock/counts/{cnt['id']}/approve",headers=h,json={'reason':'کسری انبارگردانی'}))
 assert a['status']=='approved' and a['adjusted_lines']==1
 assert D(str(stock(h,p,w)['quantity']))==7 and bal(h,'1310')-inv0==-120 and bal(h,'5200')-adj0==120
 mv=next(x for x in ok(client.get(f"/api/stock/moves?product_id={p['id']}",headers=h)) if x['kind']=='count_out');assert mv['reason']=='کسری انبارگردانی' and mv['reference']==cnt['number']
 assert client.post(f"/api/stock/counts/{cnt['id']}/approve",headers=h,json={}).status_code==409
 assert client.post(f"/api/stock/counts/{cnt['id']}/cancel",headers=h).status_code==409
 k=ok(client.get(f"/api/stock/kardex?product_id={p['id']}&warehouse_id={w['id']}",headers=h));assert k['matches_stock'] is True
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']

def test_stock_count_surplus_and_cancel_and_reserved_guard():
 h=H();p,w,sup=setup(h);buy(h,sup,p,w,4,25);c=ok(client.post('/api/customers',headers=h,json={'code':'C'+uuid.uuid4().hex[:5],'name':'c','credit_limit':10**9}))
 cnt=ok(client.post('/api/stock/counts',headers=h,json={'warehouse_id':w['id'],'product_ids':[p['id']]}))
 ok(client.post(f"/api/stock/counts/{cnt['id']}/cancel",headers=h));assert client.put(f"/api/stock/counts/{cnt['id']}/lines",headers=h,json={'lines':[{'product_id':p['id'],'counted_qty':1}]}).status_code==409
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':3}]}));ok(client.post(f"/api/orders/{o['id']}/approve",headers=h))   # ۳ رزرو
 cnt=ok(client.post('/api/stock/counts',headers=h,json={'warehouse_id':w['id'],'product_ids':[p['id']]}))
 ok(client.put(f"/api/stock/counts/{cnt['id']}/lines",headers=h,json={'lines':[{'product_id':p['id'],'counted_qty':2}]}))
 assert client.post(f"/api/stock/counts/{cnt['id']}/approve",headers=h,json={}).status_code==409            # کمتر از رزرو
 ok(client.put(f"/api/stock/counts/{cnt['id']}/lines",headers=h,json={'lines':[{'product_id':p['id'],'counted_qty':6}]}))
 a=ok(client.post(f"/api/stock/counts/{cnt['id']}/approve",headers=h,json={}));assert D(str(stock(h,p,w)['quantity']))==6 and D(str(a['ledger_value_change']))==50

def test_valuation_reconciles_with_ledger_location_and_max_stock():
 h=H();p,w,sup=setup(h,max_stock=5);buy(h,sup,p,w,8,30)
 v=ok(client.get('/api/reports/stock-valuation',headers=h));row=next(x for x in v['items'] if x['product_id']==p['id'])
 assert D(str(row['value']))==240 and v['reconciled'] is True
 st=stock(h,p,w);r=ok(client.patch(f"/api/stock/{st['id']}",headers=h,json={'location':'راهرو ۲ / قفسه ۴'}));assert r['location']=='راهرو ۲ / قفسه ۴' and stock(h,p,w)['location']
 rep=ok(client.get('/api/reports/stock',headers=h));assert any(x['product_id']==p['id'] and x['over_max'] for x in rep['over_stock'])

def test_transfer_moves_batches_and_cancel_returns_them():
 h=H();p,w,sup=setup(h,track_batch=True);w2=ok(client.post('/api/warehouses',headers=h,json={'name':'W2'+uuid.uuid4().hex[:4],'company_id':1}))
 e1=(date.today()+timedelta(days=30)).isoformat();e2=(date.today()+timedelta(days=90)).isoformat()
 buy(h,sup,p,w,4,10,batch_no='T1',expiry_date=e1);buy(h,sup,p,w,6,10,batch_no='T2',expiry_date=e2)
 t=ok(client.post('/api/stock/transfers',headers=h,json={'from_warehouse_id':w['id'],'to_warehouse_id':w2['id'],'product_id':p['id'],'quantity':5}))
 def bs(wid): return {b['batch_no']:D(str(b['quantity'])) for b in ok(client.get(f"/api/stock/batches?product_id={p['id']}&warehouse_id={wid}",headers=h))}
 assert bs(w['id'])=={'T2':5}
 ok(client.post(f"/api/stock/transfers/{t['id']}/receive",headers=h));assert bs(w2['id'])=={'T1':4,'T2':1} and bs(w['id'])=={'T2':5}
 t2=ok(client.post('/api/stock/transfers',headers=h,json={'from_warehouse_id':w['id'],'to_warehouse_id':w2['id'],'product_id':p['id'],'quantity':2}));assert bs(w['id'])=={'T2':3}
 ok(client.post(f"/api/stock/transfers/{t2['id']}/cancel",headers=h));assert bs(w['id'])=={'T2':5}
