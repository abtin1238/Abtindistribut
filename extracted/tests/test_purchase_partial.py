import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_pp.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def setup(h,sku,items):
 sid=client.post('/api/suppliers',headers=h,json={'name':'S'+sku}).json()['id']
 wid=client.get('/api/warehouses',headers=h).json()[0]['id']
 pids=[client.post('/api/products',headers=h,json={'sku':f'{sku}{i}','name':f'p{sku}{i}'}).json()['id'] for i in range(len(items))]
 return sid,wid,pids
def sup_bal(h,sid): return Decimal(str(next(x for x in client.get('/api/suppliers',headers=h).json() if x['id']==sid)['balance']))
def stock(h,wid,pid):
 return Decimal(str(sum(x['quantity'] for x in client.get('/api/stock',headers=h).json() if x['product_id']==pid and x['warehouse_id']==wid)))

def test_partial_receipt_then_complete_balances_supplier():
 h=H(); sid,wid,(p1,p2)=setup(h,'PP',[0,0])
 po=client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':wid,'items':[{'product_id':p1,'quantity':10,'unit_cost':100},{'product_id':p2,'quantity':3,'unit_cost':'33.33'}],'freight':'10'}); assert po.status_code==200,po.text
 poid=po.json()['id']; total=Decimal(po.json()['total'])
 r=client.post(f'/api/purchases/{poid}/receive',headers=h,json={'items':[{'product_id':p1,'quantity':4}]}); assert r.status_code==200,r.text
 assert r.json()['status']=='partial'; assert stock(h,wid,p1)==4 and stock(h,wid,p2)==0
 assert 0<sup_bal(h,sid)<total
 assert client.post(f'/api/purchases/{poid}/receive',headers=h,json={'items':[{'product_id':p1,'quantity':7}]}).status_code==400
 assert client.post(f'/api/purchases/{poid}/cancel',headers=h).status_code==409
 r=client.post(f'/api/purchases/{poid}/receive',headers=h); assert r.status_code==200,r.text
 assert r.json()['status']=='received'; assert stock(h,wid,p1)==10 and stock(h,wid,p2)==3
 assert sup_bal(h,sid)==total
 assert client.post(f'/api/purchases/{poid}/receive',headers=h).status_code==400

def test_cancel_draft_and_no_receive_after_cancel():
 h=H(); sid,wid,(p1,)=setup(h,'PC',[0])
 poid=client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':wid,'items':[{'product_id':p1,'quantity':1,'unit_cost':5}]}).json()['id']
 assert client.post(f'/api/purchases/{poid}/cancel',headers=h).json()['status']=='cancelled'
 assert client.post(f'/api/purchases/{poid}/receive',headers=h).status_code==409
 assert sup_bal(h,sid)==0

def test_return_capped_by_received_qty():
 h=H(); sid,wid,(p1,)=setup(h,'PR2',[0])
 poid=client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':wid,'items':[{'product_id':p1,'quantity':10,'unit_cost':10}]}).json()['id']
 client.post(f'/api/purchases/{poid}/receive',headers=h,json={'items':[{'product_id':p1,'quantity':5}]})
 assert client.post(f'/api/purchases/{poid}/return',headers=h,json={'items':[{'product_id':p1,'quantity':6}]}).status_code==400
 assert client.post(f'/api/purchases/{poid}/return',headers=h,json={'items':[{'product_id':p1,'quantity':5}]}).status_code==200

def test_allocate_cost_changes_total_and_unit_cost_only_before_receipt():
 h=H(); sid,wid,(p1,p2)=setup(h,'AC',[0,0])
 po=client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':wid,'items':[{'product_id':p1,'quantity':10,'unit_cost':100},{'product_id':p2,'quantity':10,'unit_cost':300}]}).json()
 r=client.post(f'/api/purchases/{po["id"]}/allocate-cost',headers=h,json={'label':'گمرک','amount':400}); assert r.status_code==200,r.text
 assert Decimal(r.json()['total'])==Decimal('4400.00'); assert [Decimal(x) for x in r.json()['shares']]==[Decimal('100.00'),Decimal('300.00')]
 assert client.post(f'/api/purchases/{po["id"]}/allocate-cost',headers=h,json={'label':'x','amount':0}).status_code==422
 client.post(f'/api/purchases/{po["id"]}/receive',headers=h)
 assert sup_bal(h,sid)==Decimal('4400.00')
 assert client.post(f'/api/purchases/{po["id"]}/allocate-cost',headers=h,json={'label':'late','amount':1}).status_code==409
