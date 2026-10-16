import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_followup.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
PNG=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082')
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def mk(A,role):
 client.post('/api/roles/templates',headers=A);rid=next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==role)
 u='o'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'username':u,'password':PW,'name':u,'role_id':rid,'company_ids':[]});assert r.status_code==200,r.text;return login(u,PW),r.json()['id']
def order(A,tag):
 sfx=uuid.uuid4().hex[:5];c=client.post('/api/customers',headers=A,json={'code':tag+sfx,'name':tag+sfx,'credit_limit':10**9}).json();p=client.post('/api/products',headers=A,json={'sku':tag+sfx,'name':'k'+sfx,'base_price':100}).json()
 w=client.get('/api/warehouses',headers=A).json()[0];client.post('/api/stock/adjust',headers=A,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':50,'kind':'in'})
 return client.post('/api/orders',headers=A,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json(),c

def test_visit_photo_upload_and_ownership():
 A=login();V,_=mk(A,'بازاریاب');V2,_=mk(A,'بازاریاب');o,c=order(A,'VP');v=client.post('/api/visits',headers=V,json={'customer_id':c['id']}).json();u=f"/api/visits/{v['id']}/photo"
 r=client.post(u,headers=V,files={'file':('a.png',PNG,'image/png')});assert r.status_code==200,r.text;assert r.json()['photo'].startswith('/api/documents/')
 assert client.post(u,headers=V,files={'file':('a.png',b'not an image','image/png')}).status_code==400
 assert client.post(u,headers=V2,files={'file':('a.png',PNG,'image/png')}).status_code==404
 assert next(x for x in client.get('/api/visits',headers=V).json() if x['id']==v['id'])['photo']==r.json()['photo']
 assert client.post('/api/visits/999999/photo',headers=V,files={'file':('a.png',PNG,'image/png')}).status_code==404

def test_bulk_assign_and_board():
 A=login();D,did=mk(A,'مأمور پخش');D2,_=mk(A,'مأمور پخش');o1,_=order(A,'B1');o2,_=order(A,'B2');o3,_=order(A,'B3')   # o3 تأیید نمی‌شود
 for o in (o1,o2): assert client.post(f"/api/orders/{o['id']}/approve",headers=A).status_code==200
 b=client.get('/api/deliveries/board',headers=A).json();assert {o1['id'],o2['id']}<={x['order_id'] for x in b['unassigned']} and o3['id'] not in {x['order_id'] for x in b['unassigned']}
 assert client.get('/api/deliveries/board',headers=D).status_code==403
 assert client.post('/api/deliveries/bulk-assign',headers=D,json={'order_ids':[o1['id']],'driver_id':did}).status_code==403
 r=client.post('/api/deliveries/bulk-assign',headers=A,json={'order_ids':[o1['id'],o2['id'],o3['id'],o1['id']],'driver_id':did}).json()
 assert r['assigned']==2 and [x['status'] for x in r['results']]==['ok','ok','error']
 b=client.get('/api/deliveries/board',headers=A).json();assert o1['id'] not in {x['order_id'] for x in b['unassigned']}
 mine={x['order_id'] for x in b['deliveries'] if x['driver_name']}
 assert {o1['id'],o2['id']}<=mine and all(x['customer_name'] for x in b['deliveries'])
 assert len([x for x in client.get('/api/deliveries/mine',headers=D).json()['active']])==2 and client.get('/api/deliveries/mine',headers=D2).json()['active']==[]
 assert client.post('/api/deliveries/bulk-assign',headers=A,json={'order_ids':[],'driver_id':did}).status_code==422

def test_automatic_reminders_are_idempotent():
 A=login();S,sid=mk(A,'فروشنده');today=date.today().isoformat()
 t=client.post('/api/tasks',headers=S,json={'title':'تماس '+uuid.uuid4().hex[:4],'kind':'call','due_date':today}).json()
 l=client.post('/api/leads',headers=S,json={'title':'سرنخ '+uuid.uuid4().hex[:4],'next_followup':today}).json()
 fut=client.post('/api/tasks',headers=S,json={'title':'آینده','due_date':'2999-01-01'}).json()
 assert client.post('/api/automation/run-reminders',headers=S).status_code==403
 assert client.post('/api/automation/run-reminders',headers=A).json()['notified']>=2
 ns=client.get('/api/notifications',headers=S).json();titles={n['title']:n['body'] for n in ns}
 assert titles.get('یادآوری تماس')==t['title'] and titles.get('پیگیری سرنخ')==l['title'] and 'آینده' not in titles.values()
 n1=len(ns);assert client.post('/api/automation/run-reminders',headers=A).json()['notified']==0
 assert len(client.get('/api/notifications',headers=S).json())==n1
 client.patch(f"/api/tasks/{t['id']}",headers=S,json={'status':'done'})

def test_reminder_function_directly():
 from app.core.database import SessionLocal
 from app.modules.automation import run_reminders
 with SessionLocal() as s: assert run_reminders(s,None,date(2000,1,1))==0
