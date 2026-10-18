"""مرحله ۱۶ — API یکپارچه: نسخه‌بندی، خطای واحد، Idempotency، کلید API، Rate limit، وبهوک، صفحه‌بندی، OpenAPI، sync"""
import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_stage16.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_stage16.sqlite3')
except FileNotFoundError: pass
import json
import uuid
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core import ratelimit
from app.core.config import utcnow
from app.core.database import SessionLocal
from app.models import User,WebhookDelivery,WebhookEndpoint
from app.services import webhooks as wh
client=TestClient(app)
PW='Test-pass-123'
def login(u='admin',p='test-password'):
 r=client.post('/api/auth/login',json={'username':u,'password':p});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def role_id(A,name):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==name)
def mkuser(A,role):
 u='s'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'branch_id':1,'username':u,'password':PW,'name':u,'role_id':role_id(A,role),'company_ids':[]});assert r.status_code==200,r.text;return login(u,PW)
def admin_role(A): return next(r['id'] for r in client.get('/api/roles',headers=A).json() if '*' in (r['permissions'] or []))
def cust(A,tag='C'): return client.post('/api/customers',headers=A,json={'code':tag+uuid.uuid4().hex[:6],'name':tag,'credit_limit':10**6})

def test_v1_prefix_is_alias_and_headers():
 A=login();a=client.get('/api/customers',headers=A);b=client.get('/api/v1/customers',headers=A)
 assert a.status_code==b.status_code==200 and a.json()==b.json() and b.headers['X-API-Version']=='1'
 assert client.get('/api/v1/health').json()['ok'] and client.get('/health').json()['api_version']=='v1' and client.get('/api/v1/ready').json()['db'] is True
def test_unified_error_format_and_request_id():
 r=client.get('/api/v1/customers');j=r.json()
 assert r.status_code==401 and j['code']=='unauthorized' and j['message']==j['detail'] and j['request_id']==r.headers['X-Request-ID']
 assert client.get('/api/v1/nope',headers=login()).json()['code']=='not_found'
 r=client.post('/api/v1/customers',headers={**login(),'X-Request-ID':'trace-abc-12345'},json={'name':''});j=r.json()
 assert r.status_code==422 and j['code']=='validation_error' and j['request_id']=='trace-abc-12345' and j['details'][0]['field'] and isinstance(j['detail'],list)
 assert client.get('/api/v1/customers',headers={'X-Request-ID':'bad id!'}).headers['X-Request-ID']!='bad id!'   # شناسه‌ی نامعتبر جایگزین می‌شود
def test_pagination_headers():
 A=login()
 for _ in range(3): assert cust(A,'P').status_code==200
 r=client.get('/api/v1/customers?limit=2&offset=0',headers=A);t=int(r.headers['X-Total-Count'])
 assert len(r.json())==2 and t>=3 and r.headers['X-Limit']=='2'
 rest=client.get(f'/api/v1/customers?limit=1000&offset=2',headers=A).json();assert len(rest)==t-2
 assert client.get('/api/v1/customers?limit=0',headers=A).status_code==422
def test_idempotency_key_replays_and_detects_reuse():
 A=login();k='idem-'+uuid.uuid4().hex;body={'code':'ID'+uuid.uuid4().hex[:6],'name':'idem','credit_limit':10}
 r1=client.post('/api/v1/customers',headers={**A,'Idempotency-Key':k},json=body);r2=client.post('/api/v1/customers',headers={**A,'Idempotency-Key':k},json=body)
 assert r1.status_code==r2.status_code==200 and r1.json()['id']==r2.json()['id'] and r2.headers.get('Idempotency-Replayed')=='true' and 'Idempotency-Replayed' not in r1.headers
 assert sum(1 for c in client.get('/api/customers',headers=A).json() if c['code']==body['code'])==1   # فقط یک‌بار ساخته شد
 r3=client.post('/api/v1/customers',headers={**A,'Idempotency-Key':k},json={**body,'name':'other'});assert r3.status_code==422 and r3.json()['code']=='idempotency_key_reuse'
 assert client.post('/api/v1/customers',headers={**A,'Idempotency-Key':'x'},json=body).json()['code']=='invalid_idempotency_key'
def test_idempotency_does_not_cache_auth_failures_and_is_per_credential():
 A=login();B=login();k='idem-'+uuid.uuid4().hex;body={'code':'IC'+uuid.uuid4().hex[:6],'name':'x','credit_limit':1}
 bad=client.post('/api/v1/customers',headers={'Authorization':'Bearer nope','Idempotency-Key':k},json=body);assert bad.status_code==401
 ok=client.post('/api/v1/customers',headers={**A,'Idempotency-Key':k},json=body);assert ok.status_code==200
 other=client.post('/api/v1/customers',headers={**B,'Idempotency-Key':k},json={**body,'code':body['code']+'b'});assert other.status_code==200 and other.json()['id']!=ok.json()['id']
def test_api_key_lifecycle_and_limits():
 A=login();rid=admin_role(A)
 r=client.post('/api/v1/api-keys',headers=A,json={'name':'erp','role_id':rid,'expires_in_days':30});assert r.status_code==201,r.text;k=r.json();key=k['key']
 assert key.startswith(k['prefix']+'_') and 'key_hash' not in k and k['active']
 assert 'key' not in client.get('/api/v1/api-keys',headers=A).json()[0] and all('key_hash' not in x for x in client.get('/api/v1/api-keys',headers=A).json())
 K={'X-API-Key':key};assert client.get('/api/v1/customers',headers=K).status_code==200
 assert client.get('/api/v1/customers',headers={'Authorization':'Bearer '+key}).status_code==200
 assert client.get('/api/v1/api-keys',headers=K).status_code==403 and client.post('/api/v1/webhooks',headers=K,json={'url':'https://example.com/h'}).status_code==403   # مدیریت با کلید API ممنوع
 assert client.get('/api/v1/customers',headers={'X-API-Key':key[:-1]+('a' if key[-1]!='a' else 'b')}).status_code==401
 assert client.get('/api/v1/customers',headers={'X-API-Key':'abk_zzzzzzzz_foo'}).status_code==401
 assert client.delete(f"/api/v1/api-keys/{k['id']}",headers=A).json()['active'] is False
 assert client.get('/api/v1/customers',headers=K).status_code==401
def test_api_key_role_cannot_exceed_creator_and_expiry():
 A=login();S=mkuser(A,'مدیر فروش')   # دسترسی admin.write ندارد
 assert client.post('/api/v1/api-keys',headers=S,json={'name':'x','role_id':admin_role(A)}).status_code==403
 r=client.post('/api/v1/api-keys',headers=A,json={'name':'short','role_id':role_id(A,'فروشنده'),'expires_in_days':1}).json()
 with SessionLocal() as s:
  from app.models import ApiKey
  k=s.get(ApiKey,r['id']);k.expires_at=utcnow()-timedelta(seconds=1);s.commit()
 assert client.get('/api/v1/customers',headers={'X-API-Key':r['key']}).status_code==401
 low=client.post('/api/v1/api-keys',headers=A,json={'name':'seller','role_id':role_id(A,'فروشنده')}).json()   # کلید با نقش محدود: دسترسی‌های همان نقش
 assert client.get('/api/v1/reports/sales',headers={'X-API-Key':low['key']}).status_code==403
def test_rate_limit_headers_and_429(monkeypatch):
 A=login();monkeypatch.setenv('RATE_LIMIT_PER_MIN','3');ratelimit.LIMITER.reset()
 rs=[client.get('/api/v1/customers',headers=A) for _ in range(4)]
 assert [r.status_code for r in rs]==[200,200,200,429] and rs[0].headers['X-RateLimit-Limit']=='3' and rs[2].headers['X-RateLimit-Remaining']=='0'
 assert rs[3].json()['code']=='rate_limited' and int(rs[3].headers['Retry-After'])>=1
 assert client.get('/api/v1/health').status_code==200   # health محدود نمی‌شود
 monkeypatch.setenv('RATE_LIMIT_PER_MIN','0');ratelimit.LIMITER.reset()
def test_login_rate_limit(monkeypatch):
 monkeypatch.setenv('RATE_LIMIT_LOGIN_PER_MIN','2');ratelimit.LIMITER.reset()
 c=[client.post('/api/v1/auth/login',json={'username':'admin','password':'bad'}).status_code for _ in range(3)]
 assert c==[401,401,429];monkeypatch.setenv('RATE_LIMIT_LOGIN_PER_MIN','0');ratelimit.LIMITER.reset()
def test_limiter_sliding_window_unit():
 L=ratelimit.Limiter();assert [L.hit('k',2,60,now=t)[0] for t in (0,1,2)]==[True,True,False]
 assert L.hit('k',2,60,now=60.5)[0] and L.hit('other',2,60,now=2)[0]
def test_openapi_is_versioned_with_security_schemes():
 j=client.get('/api/v1/openapi.json').json()
 assert '/api/v1/customers' in j['paths'] and not any(p.startswith('/api/customers') for p in j['paths']) and set(j['components']['securitySchemes'])>={'bearerAuth','apiKeyAuth'}
 assert j['paths']['/api/v1/customers']['get']['tags']==['customers'] and client.get('/docs').status_code==200

def mk_hook(A,events=None,url='https://hooks.example.com/abtin'):
 r=client.post('/api/v1/webhooks',headers=A,json={'url':url,'events':events or ['*']});assert r.status_code==201,r.text;return r.json()
def test_webhook_crud_validation_and_secret_shown_once():
 A=login();h=mk_hook(A,['order.created'])
 assert h['secret'].startswith('whsec_') and all('secret' not in x for x in client.get('/api/v1/webhooks',headers=A).json())
 assert client.post('/api/v1/webhooks',headers=A,json={'url':'http://hooks.example.com/x'}).status_code==400          # http مجاز نیست
 assert client.post('/api/v1/webhooks',headers=A,json={'url':'https://u:p@hooks.example.com/x'}).status_code==400
 assert client.post('/api/v1/webhooks',headers=A,json={'url':'https://hooks.example.com/x','events':['bogus.event']}).status_code==400
 assert client.get('/api/v1/webhooks/events',headers=A).json()
 r=client.post(f"/api/v1/webhooks/{h['id']}/rotate-secret",headers=A).json();assert r['secret']!=h['secret']
 assert client.patch(f"/api/v1/webhooks/{h['id']}",headers=A,json={'active':False}).json()['active'] is False
 assert client.delete(f"/api/v1/webhooks/{h['id']}",headers=A).json()['ok'] and client.get(f"/api/v1/webhooks/{h['id']}/deliveries",headers=A).status_code==404
def test_ssrf_guard(monkeypatch):
 monkeypatch.setenv('WEBHOOK_ALLOW_PRIVATE','0')
 for u in ('https://127.0.0.1/x','https://localhost/x','https://10.0.0.5/x','https://169.254.169.254/latest','https://[::1]/x','ftp://example.com/x','https://u@example.com/x'):
  try: wh.check_url(u);assert False,u
  except wh.UrlRejected: pass
 assert wh.check_url('https://8.8.8.8/hook')=='https://8.8.8.8/hook'
def test_webhook_signature_delivery_and_retry_backoff():
 A=login();h=mk_hook(A,['stock.low','system.notice']);sent=[]
 with SessionLocal() as s:
  cid=s.get(WebhookEndpoint,h['id']).company_id
  assert wh.emit_event(s,cid,'stock.low',{'sku':'X'},dedupe='low:X:1')>=1 and wh.emit_event(s,cid,'stock.low',{'sku':'X'},dedupe='low:X:1')==0   # dedupe
  s.commit()
  def ok(url,body,headers): sent.append((url,body,headers));return 200,''
  wh.dispatch_webhooks(s,limit=500,post=ok)
 mine=[x for x in sent if x[0]=='https://hooks.example.com/abtin']
 assert mine
 url,body,hd=mine[0];ts=int(hd['X-Abtin-Timestamp'])
 old=wh.sign('s',ts,body);assert old.startswith('v1=') and old==wh.sign('s',ts,body)!=wh.sign('s2',ts,body)
 assert json.loads(body)['event'] in ('stock.low','system.notice') and hd['X-Abtin-Event']==json.loads(body)['event']
 # شکست → backoff پلکانی → failed بعد از ۶ تلاش
 with SessionLocal() as s:
  cid=s.get(WebhookEndpoint,h['id']).company_id;wh.emit_event(s,cid,'system.notice',{'m':1},dedupe='fail-1');s.commit()
  did=s.scalars(__import__('sqlalchemy').select(WebhookDelivery.id).where(WebhookDelivery.endpoint_id==h['id'],WebhookDelivery.event_id==__import__('hashlib').sha1(b'fail-1').hexdigest()[:32])).one()
  bad=lambda url,body,headers:(500,'HTTP 500')
  for i in range(wh.MAX_ATTEMPTS):
   d=s.get(WebhookDelivery,did);d.next_try_at=utcnow()-timedelta(seconds=1);s.commit();wh.dispatch_webhooks(s,limit=500,post=bad);s.refresh(d)
   if i<wh.MAX_ATTEMPTS-1: assert d.status=='pending' and d.attempts==i+1 and d.next_try_at>utcnow()+timedelta(seconds=wh.BACKOFF[i]-5)
  assert d.status=='failed' and d.attempts==wh.MAX_ATTEMPTS and d.response_code==500
 assert client.post(f"/api/v1/webhook-deliveries/{did}/redeliver",headers=A).json()['status']=='pending'
def test_webhook_test_endpoint_and_notify_hook(monkeypatch):
 A=login();h=mk_hook(A,['order.created']);calls=[]
 monkeypatch.setattr(wh,'http_post',lambda url,body,headers:(calls.append(headers) or (204,'')))
 r=client.post(f"/api/v1/webhooks/{h['id']}/test",headers=A).json();assert r['status']=='delivered' and calls[0]['X-Abtin-Event']=='webhook.test'
 monkeypatch.setattr(wh,'http_post',lambda url,body,headers:(None,'connection refused'))
 r=client.post(f"/api/v1/webhooks/{h['id']}/test",headers=A).json();assert r['status']=='failed' and 'connection' in r['error']
 from app.services.notify import notify
 with SessionLocal() as s:
  u=s.scalar(__import__('sqlalchemy').select(User).where(User.username=='admin'));n=notify(s,1,[u.id],'order_new','سفارش جدید','x','order',7,dedupe='hook-order-7');s.commit()
  ds=s.scalars(__import__('sqlalchemy').select(WebhookDelivery).where(WebhookDelivery.endpoint_id==h['id'],WebhookDelivery.event=='order.created')).all()
  assert len(ds)==1 and ds[0].payload['data']['entity_id']==7 and ds[0].status=='pending'
def test_sync_conflict_code_and_my_events():
 A=login();c=cust(A,'SY').json();ev=lambda *e:client.post('/api/v1/sync',headers=A,json={'events':list(e)}).json()['results']
 r=ev({'id':'cs-'+c['code'],'type':'visit.start','payload':{'customer_id':c['id']}},{'id':'cf1-'+c['code'],'type':'visit.finish','ref':'cs-'+c['code']},{'id':'cf2-'+c['code'],'type':'visit.finish','ref':'cs-'+c['code'],'payload':{'note':'late'}})
 assert [x['status'] for x in r]==['applied','applied','rejected'] and r[2]['code']=='conflict' and 'code' not in r[0]
 mine=client.get('/api/v1/sync/events?status=rejected',headers=A).json();assert any(x['id']=='cf2-'+c['code'] for x in mine)
