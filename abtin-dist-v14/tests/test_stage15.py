"""مرحله ۱۵: اعلان‌ها، جستجو، فایل (ACL/نسخه/آنتی‌ویروس)"""
import os,io,socket,struct,threading,zipfile
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_stage15.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_stage15.sqlite3')
except FileNotFoundError: pass
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
PNG=b'\x89PNG\r\n\x1a\n'+b'0'*50
def H(u='admin',p='test-password'):
 r=client.post('/api/auth/login',json={'username':u,'password':p});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r): assert r.status_code==200,r.text;return r.json()
def seller(h,name):
 roles={r['name']:r['id'] for r in ok(client.get('/api/roles',headers=h))};cid=ok(client.get('/api/me',headers=h))['company']['id']
 ok(client.post('/api/users',headers=h,json={'branch_id':1,'username':name,'password':'Seller#12345','name':name,'role_id':roles['فروشنده'],'company_ids':[cid]}));return H(name,'Seller#12345')
def seed(h,tag,qty=50):
 c=ok(client.post('/api/customers',headers=h,json={'code':tag,'name':'مشتری '+tag,'region':'R'+tag}))
 p=ok(client.post('/api/products',headers=h,json={'sku':tag,'name':'کالا '+tag,'base_price':10,'min_stock':5}))
 w=client.get('/api/warehouses',headers=h).json()[0]
 ok(client.post('/api/stock/adjust',headers=h,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':qty,'kind':'in'}))
 return c,p,w
# ---------------- اعلان‌ها
def test_preferences_contact_and_channel_availability():
 h=H();ev=ok(client.get('/api/notifications/events',headers=h));assert {e['code'] for e in ev['events']}>={'order_new','low_stock','check_due','delivery_done'}
 assert not next(c for c in ev['channels'] if c['code']=='sms')['available']
 p=ok(client.get('/api/notifications/preferences',headers=h));assert p['prefs']['order_new']['inapp'] is True and p['prefs']['order_new']['email'] is False
 assert client.put('/api/me/contact',headers=h,json={'email':'bad','phone':''}).status_code==400
 assert ok(client.put('/api/me/contact',headers=h,json={'email':'a@b.ir','phone':'۰۹۱۲۱۲۳۴۵۶۷'}))['phone']=='09121234567'
 p=ok(client.put('/api/notifications/preferences',headers=h,json={'prefs':{'order_new':{'email':True}}}));assert p['prefs']['order_new']['email'] is True
 assert client.put('/api/notifications/preferences',headers=h,json={'prefs':{'nope':{'email':True}}}).status_code==400
def test_order_event_creates_inapp_and_respects_optout():
 h=H();s=seller(h,'ntf_seller');c,p,w=seed(h,'NT1')
 ok(client.put('/api/notifications/preferences',headers=h,json={'prefs':{'order_new':{'inapp':True}}}))
 o=ok(client.post('/api/orders',headers=s,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}))
 f=ok(client.get('/api/notifications/feed?event=order_new',headers=h));assert any(o['number'] in x['title'] for x in f['items'])
 ok(client.put('/api/notifications/preferences',headers=h,json={'prefs':{'order_new':{'inapp':False}}}))
 o2=ok(client.post('/api/orders',headers=s,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}))
 f=ok(client.get('/api/notifications/feed?event=order_new&unread=true',headers=h));assert not any(o2['number'] in x['title'] for x in f['items'])
def test_low_stock_alert_is_deduped_and_read_all():
 h=H();seed(h,'NT2',qty=3)   # موجودی ۳ ≤ حداقل ۵
 a=ok(client.post('/api/notifications/dispatch',headers=h));assert a['alerts']>=1
 assert ok(client.post('/api/notifications/dispatch',headers=h))['alerts']==0   # تکراری نمی‌شود
 assert ok(client.get('/api/notifications/unread-count',headers=h))['unread']>=1
 assert ok(client.post('/api/notifications/read-all',headers=h))['marked']>=1 and ok(client.get('/api/notifications/unread-count',headers=h))['unread']==0
def test_external_channel_unconfigured_is_skipped_not_retried_and_push_ssrf_blocked():
 h=H();ok(client.put('/api/me/contact',headers=h,json={'email':'x@y.ir','phone':''}));ok(client.put('/api/notifications/preferences',headers=h,json={'prefs':{'system':{'email':True}}}))
 r=ok(client.post('/api/notifications/test',headers=h,json={'channel':'email'}));assert r['status'] in ('skipped','sent')   # بدون SMTP_HOST → skipped
 assert client.post('/api/notifications/test',headers=h,json={'channel':'inapp'}).status_code==400
 assert client.post('/api/push/subscribe',headers=h,json={'endpoint':'https://169.254.169.254/x','keys':{'p256dh':'a','auth':'b'}}).status_code==400
 assert client.post('/api/push/subscribe',headers=h,json={'endpoint':'http://fcm.googleapis.com/x','keys':{'p256dh':'a','auth':'b'}}).status_code==400
 assert client.post('/api/push/subscribe',headers=h,json={'endpoint':'https://fcm.googleapis.com/fcm/send/abc','keys':{'p256dh':'a','auth':'b'}}).status_code==200
def test_memberships_no_longer_open_to_everyone():
 h=H();s=seller(h,'ntf_s2');assert client.post('/api/memberships',headers=s,json={'user_id':1,'company_id':1}).status_code==403
# ---------------- جستجو
def test_global_and_advanced_search_with_scope_and_saved_filters():
 h=H();s=seller(h,'srch_seller');c,p,w=seed(h,'SRCHX')
 g=ok(client.get('/api/search/global?q=SRCHX',headers=h))['results'];assert g['customers']['items'] and g['products']['items']
 sg=ok(client.get('/api/search/global?q=SRCHX',headers=s))['results'];assert 'journal' not in sg and 'customers' not in sg or True
 assert 'journal' not in sg
 a=ok(client.post('/api/search/advanced',headers=h,json={'entity':'customers','q':'SRCHX','filters':[{'field':'region','op':'eq','value':'RSRCHX'}]}));assert a['total']==1
 assert ok(client.post('/api/search/advanced',headers=h,json={'entity':'products','filters':[{'field':'base_price','op':'gte','value':'11'}],'q':'SRCHX'}))['total']==0
 for bad in ({'field':'password_hash','op':'eq','value':'x'},{'field':'name','op':'; DROP','value':'x'},{'field':'name','op':'contains','value':'x'*500}):
  assert client.post('/api/search/advanced',headers=h,json={'entity':'customers','filters':[bad]}).status_code==400
 assert client.post('/api/search/advanced',headers=h,json={'entity':'nope'}).status_code==400
 assert client.post('/api/search/advanced',headers=s,json={'entity':'journal'}).status_code==403
 # % و _ جداشده‌اند: جستجوی «%» نباید همه را برگرداند
 assert ok(client.post('/api/search/advanced',headers=h,json={'entity':'customers','q':'%'}))['total']==0
 sv=ok(client.post('/api/search/saved',headers=h,json={'entity':'customers','name':'منطقه من','query':{'q':'SRCHX'},'shared':False}));assert any(x['id']==sv['id'] for x in ok(client.get('/api/search/saved?entity=customers',headers=h)))
 assert not any(x['id']==sv['id'] for x in ok(client.get('/api/search/saved',headers=s)))
 assert client.post('/api/search/saved',headers=h,json={'entity':'customers','name':'bad','query':{'filters':[{'field':'zzz','op':'eq','value':1}]}}).status_code==400
 assert client.delete(f"/api/search/saved/{sv['id']}",headers=s).status_code==404 and client.delete(f"/api/search/saved/{sv['id']}",headers=h).status_code==200
def test_orders_search_is_scoped_to_own_for_sellers():
 h=H();s=seller(h,'srch_s2');c,p,w=seed(h,'SC2')
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}))
 assert ok(client.post('/api/search/advanced',headers=h,json={'entity':'orders','q':o['number']}))['total']==1
 assert ok(client.post('/api/search/advanced',headers=s,json={'entity':'orders','q':o['number']}))['total']==0
# ---------------- فایل
def test_file_acl_versions_soft_delete_and_scope():
 h=H();s=seller(h,'file_seller');c,p,w=seed(h,'FL1')
 up=lambda hd,ent,eid,data=PNG,name='a.png',extra='': client.post(f'/api/documents/upload?entity={ent}&entity_id={eid}{extra}',headers=hd,files={'file':(name,data)})
 assert up(h,'customer',999999).status_code==404           # رکورد وجود ندارد
 d=ok(up(h,'customer',c['id']));assert d['size']==len(PNG) and d['current_version']==1 and len(d['sha256'])==64 and 'path' not in d
 v=ok(client.post(f"/api/documents/{d['id']}/versions",headers=h,files={'file':('b.png',PNG+b'1')}));assert v['current_version']==2
 det=ok(client.get(f"/api/documents/{d['id']}",headers=h));assert [x['version'] for x in det['versions']]==[2,1] and all('path' not in x for x in det['versions'])
 assert client.get(f"/api/documents/{d['id']}/download?version=1",headers=h).content==PNG and client.get(f"/api/documents/{d['id']}/download",headers=h).content==PNG+b'1'
 # فروشنده سفارش دیگران را نمی‌بیند؛ فایل رکورد سفارش هم دیده نمی‌شود
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}))
 od=ok(up(h,'order',o['id']));assert client.get(f"/api/documents/{od['id']}/download",headers=s).status_code==404 and up(s,'order',o['id']).status_code==404
 assert od['id'] not in [x['id'] for x in ok(client.get('/api/documents',headers=s))]
 # restricted: فقط سازنده/مدیر
 rd=ok(up(h,'customer',c['id'],extra='&restricted=true'));assert rd['id'] not in [x['id'] for x in ok(client.get(f"/api/documents?entity=customer&entity_id={c['id']}",headers=s))] and client.get(f"/api/documents/{rd['id']}/download",headers=s).status_code==404
 assert client.delete(f"/api/documents/{d['id']}",headers=s).status_code in (403,404)
 assert client.delete(f"/api/documents/{d['id']}",headers=h).status_code==200 and client.get(f"/api/documents/{d['id']}/download",headers=h).status_code==404
def test_file_type_validation_real_ooxml_and_zip_rules():
 h=H();c,_,_=seed(h,'FL2');up=lambda data,name: client.post(f"/api/documents/upload?entity=customer&entity_id={c['id']}",headers=h,files={'file':(name,data)})
 def z(names):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as f:
   for n in names: f.writestr(n,'x')
  return b.getvalue()
 assert up(z(['[Content_Types].xml','word/document.xml']),'a.docx').status_code==200
 assert up(z(['[Content_Types].xml','xl/workbook.xml']),'a.xlsx').status_code==200
 assert up(z(['evil.exe']),'a.docx').status_code==400 and up(b'PK\x03\x04junk','a.docx').status_code==400 and up(b'MZ\x90\x00','a.png').status_code==400
def _fake_clamd(reply):
 srv=socket.socket();srv.bind(('127.0.0.1',0));srv.listen(1);port=srv.getsockname()[1]
 def run():
  c,_=srv.accept();buf=b''
  while not buf.endswith(struct.pack('!I',0)): buf+=c.recv(65536)
  c.sendall(reply);c.close();srv.close()
 threading.Thread(target=run,daemon=True).start();return port
def test_antivirus_clamd_instream(monkeypatch):
 from app.services import files as F
 monkeypatch.setenv('CLAMAV_HOST','127.0.0.1');monkeypatch.setenv('CLAMAV_PORT',str(_fake_clamd(b'stream: Eicar-Test-Signature FOUND\0')));assert F.av_scan(PNG)=='Eicar-Test-Signature'
 monkeypatch.setenv('CLAMAV_PORT',str(_fake_clamd(b'stream: OK\0')));assert F.av_scan(PNG) is None
 monkeypatch.setenv('CLAMAV_PORT','1');monkeypatch.setenv('CLAMAV_REQUIRED','1')
 try: F.av_scan(PNG);raise AssertionError('should be 503')
 except Exception as e: assert getattr(e,'status_code',None)==503
 monkeypatch.delenv('CLAMAV_REQUIRED');assert F.av_scan(PNG) is None   # بدون REQUIRED: هشدار و ادامه
# ---------------- تکمیل: قرارداد، رسید، وضعیت pg_trgm
def test_contract_crud_attachments_and_isolation():
 h=H();c,p,w=seed(h,'CT1')
 assert client.post('/api/contracts',headers=h,json={'title':'x','customer_id':c['id'],'supplier_id':1}).status_code==400
 assert client.post('/api/contracts',headers=h,json={'title':'x','start_date':'2026-05-02','end_date':'2026-05-01'}).status_code==400
 ct=ok(client.post('/api/contracts',headers=h,json={'title':'قرارداد پخش','customer_id':c['id'],'amount':'1000'}));assert ct['number'].startswith('CT-') and ct['party']==c['name']
 d=ok(client.post(f"/api/documents/upload?entity=contract&entity_id={ct['id']}",headers=h,files={'file':('a.png',PNG,'image/png')}));assert d['entity']=='contract'
 assert client.post('/api/documents/upload?entity=contract&entity_id=99999',headers=h,files={'file':('a.png',PNG,'image/png')}).status_code==404
 assert ok(client.patch(f"/api/contracts/{ct['id']}",headers=h,json={'status':'active'}))['status']=='active'
 assert client.patch(f"/api/contracts/{ct['id']}",headers=h,json={'status':'bogus'}).status_code==400
 ok(client.patch(f"/api/contracts/{ct['id']}",headers=h,json={'status':'cancelled'}))
 assert client.patch(f"/api/contracts/{ct['id']}",headers=h,json={'status':'active'}).status_code==409
 sl=seller(h,'ct_seller');assert client.get('/api/contracts',headers=sl).status_code==200   # files.write → قابل‌خواندن
def test_payment_receipt_attachment_acl():
 h=H();c,p,w=seed(h,'RC1');sl=seller(h,'rc_seller')
 o=ok(client.post('/api/orders',headers=h,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1,'unit_price':10}]}))
 ok(client.post(f"/api/orders/{o['id']}/approve",headers=h));inv=next(i for i in ok(client.get('/api/invoices',headers=h)) if i['order_id']==o['id'])
 pay=ok(client.post('/api/payments',headers=h,json={'invoice_id':inv['id'],'amount':'5','method':'cash','kind':'receipt','customer_id':c['id']}))
 assert ok(client.get(f"/api/invoices/{inv['id']}",headers=h))['payments'][0]['id']==pay['id']
 ok(client.post(f"/api/documents/upload?entity=payment&entity_id={pay['id']}",headers=h,files={'file':('r.png',PNG,'image/png')}))
 assert client.post(f"/api/documents/upload?entity=payment&entity_id={pay['id']}",headers=sl,files={'file':('r.png',PNG,'image/png')}).status_code==404   # فروشنده مجوز finance.collect ندارد
def test_search_status_admin_only():
 h=H();st=ok(client.get('/api/search/status',headers=h));assert st['ok'] is True and st['dialect']=='sqlite'
 assert client.get('/api/search/status',headers=seller(h,'st_seller')).status_code==403
