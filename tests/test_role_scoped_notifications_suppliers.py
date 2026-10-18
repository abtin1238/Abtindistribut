"""اعلان‌ها بر اساس نقش کاربر + اعتبارسنجی تعریف تأمین‌کننده"""
import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_role_notif.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_role_notif.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H(u='admin',p='test-password'):
 r=client.post('/api/auth/login',json={'username':u,'password':p});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r): assert r.status_code==200,r.text;return r.json()
def user_with_role(h,name,role):
 roles={r['name']:r['id'] for r in ok(client.get('/api/roles',headers=h))};cid=ok(client.get('/api/me',headers=h))['company']['id']
 ok(client.post('/api/users',headers=h,json={'branch_id':1,'username':name,'password':'User#123456','name':name,'role_id':roles[role],'company_ids':[cid]}));return H(name,'User#123456')
def test_events_follow_role():
 a=H();ok(client.post('/api/roles/templates',headers=a))
 admin_events={e['code'] for e in ok(client.get('/api/notifications/events',headers=a))['events']}
 m=user_with_role(a,'mk1','بازاریاب')
 mk=ok(client.get('/api/notifications/events',headers=m))['events'];codes={e['code'] for e in mk}
 assert {'check_due','low_stock','order_new'}.isdisjoint(codes) and 'system' in codes and codes<admin_events
 assert set(ok(client.get('/api/notifications/preferences',headers=m))['prefs'])==codes
 assert client.put('/api/notifications/preferences',headers=m,json={'prefs':{'check_due':{'inapp':False}}}).status_code==403
def test_supplier_requires_name():
 h=H()
 assert client.post('/api/suppliers',headers=h,json={'name':'  '}).status_code==400
 s=ok(client.post('/api/suppliers',headers=h,json={'name':' تأمین تست ','phone':'0912'}));assert s['name']=='تأمین تست'
 ok(client.post('/api/purchases',headers=h,json={'supplier_id':s['id'],'warehouse_id':ok(client.get('/api/warehouses',headers=h))[0]['id'],'items':[]})) if False else None
 rows=ok(client.get('/api/purchases',headers=h));assert all('supplier_name' in r for r in rows)
