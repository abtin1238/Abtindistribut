import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s1sec.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
import app.modules.auth_org.service as svc

RH={'X-Requested-With':'abtin'}

def browser(): return TestClient(app)

def login(c,u='admin',pw='test-password'):
 r=c.post('/api/auth/login',json={'username':u,'password':pw}); assert r.status_code==200,r.text
 return r

def H(r): return {'Authorization':'Bearer '+r.json()['token']}

def test_login_sets_httponly_strict_cookie_and_short_access():
 c=browser(); r=login(c); sc=r.headers['set-cookie'].lower()
 assert 'abtin_rt=' in sc and 'httponly' in sc and 'samesite=strict' in sc and 'path=/api' in sc
 assert 'refresh' not in r.text.lower() and r.json()['expires_in']<=svc.ACCESS_TOKEN_MINUTES*60

def test_refresh_requires_header_and_cookie():
 c=browser(); assert c.post('/api/auth/refresh').status_code==400
 assert c.post('/api/auth/refresh',headers=RH).status_code==401
 login(c); assert c.post('/api/auth/refresh').status_code==400

def test_refresh_rotates_and_revokes_old_access():
 c=browser(); r=login(c); old=H(r)
 r2=c.post('/api/auth/refresh',headers=RH); assert r2.status_code==200,r2.text
 new=H(r2); assert new!=old
 assert c.get('/api/me',headers=new).status_code==200
 assert c.get('/api/me',headers=old).status_code==401

def test_refresh_reuse_after_grace_revokes_family():
 c=browser(); login(c); stolen=c.cookies.get('abtin_rt')
 r2=c.post('/api/auth/refresh',headers=RH); assert r2.status_code==200
 good=H(r2)
 svc.REFRESH_REUSE_GRACE_SECONDS,keep=-1,svc.REFRESH_REUSE_GRACE_SECONDS
 try:
  thief=browser(); thief.cookies.set('abtin_rt',stolen,path='/api')
  assert thief.post('/api/auth/refresh',headers=RH).status_code==401
 finally: svc.REFRESH_REUSE_GRACE_SECONDS=keep
 assert c.get('/api/me',headers=good).status_code==401
 assert c.post('/api/auth/refresh',headers=RH).status_code==401

def test_reuse_within_grace_does_not_kill_family():
 c=browser(); login(c); first=c.cookies.get('abtin_rt')
 r2=c.post('/api/auth/refresh',headers=RH); assert r2.status_code==200
 other=browser(); other.cookies.set('abtin_rt',first,path='/api')
 assert other.post('/api/auth/refresh',headers=RH).status_code==401
 assert c.get('/api/me',headers=H(r2)).status_code==200
 assert c.post('/api/auth/refresh',headers=RH).status_code==200

def test_logout_revokes_refresh():
 c=browser(); r=login(c); saved=c.cookies.get('abtin_rt')
 assert c.post('/api/auth/logout',headers=H(r)).status_code==200
 other=browser(); other.cookies.set('abtin_rt',saved,path='/api')
 assert other.post('/api/auth/refresh',headers=RH).status_code==401

def test_logout_all_and_change_password_revoke_other_refresh():
 a=browser(); b=browser(); ra=login(a); login(b)
 assert a.post('/api/auth/logout-all',headers=H(ra)).status_code==200
 assert b.post('/api/auth/refresh',headers=RH).status_code==401
 assert a.post('/api/auth/refresh',headers=RH).status_code==200
 c=browser(); d=browser(); rc=login(c); login(d)
 r=c.post('/api/auth/change-password',headers=H(rc),json={'old_password':'test-password','new_password':'Stage1-new-pass-12'}); assert r.status_code==200,r.text
 assert d.post('/api/auth/refresh',headers=RH).status_code==401
 assert c.post('/api/auth/refresh',headers=RH).status_code==200
 # بازگرداندن رمز برای تست‌های بعدی
 e=browser(); re_=login(e,pw='Stage1-new-pass-12')
 assert e.post('/api/auth/change-password',headers=H(re_),json={'old_password':'Stage1-new-pass-12','new_password':'test-password'}).status_code==200

def _mkuser(c,h,name,pw='Valid-pass-123'):
 roles=c.get('/api/roles',headers=h).json(); rid=next(r['id'] for r in roles if r['name']=='فروشنده')
 return c.post('/api/users',headers=h,json={'username':name,'password':pw,'name':name,'role_id':rid})

def test_add_user_enforces_password_policy():
 c=browser(); h=H(login(c))
 c.post('/api/roles/templates',headers=h)
 assert _mkuser(c,h,'weak1','1234').status_code==400
 assert _mkuser(c,h,'weak2','weak2').status_code==400

def test_admin_reset_password_revokes_sessions_and_policy():
 c=browser(); h=H(login(c)); c.post('/api/roles/templates',headers=h)
 r=_mkuser(c,h,'resetme'); assert r.status_code==200,r.text; uid=r.json()['id']
 u=browser(); ur=login(u,'resetme','Valid-pass-123')
 assert c.post(f'/api/users/{uid}/reset-password',headers=h,json={'new_password':'123'}).status_code==400
 assert c.post(f'/api/users/{uid}/reset-password',headers=h,json={'new_password':'Brand-new-pass-9'}).status_code==200
 assert u.get('/api/me',headers=H(ur)).status_code==401
 assert u.post('/api/auth/refresh',headers=RH).status_code==401
 assert browser().post('/api/auth/login',json={'username':'resetme','password':'Valid-pass-123'}).status_code==401
 login(browser(),'resetme','Brand-new-pass-9')
 # کاربر عادی نباید بتواند رمز دیگران را بازنشانی کند
 uh=H(login(browser(),'resetme','Brand-new-pass-9'))
 assert browser().post(f'/api/users/{uid}/reset-password',headers=uh,json={'new_password':'Another-pass-99'}).status_code in (400,403)
 assert c.post(f'/api/users/{1}/reset-password',headers=h,json={'new_password':'Another-pass-99'}).status_code in (400,403,404)

def test_deactivated_user_cannot_refresh():
 c=browser(); h=H(login(c)); c.post('/api/roles/templates',headers=h)
 r=_mkuser(c,h,'tobeoff'); assert r.status_code==200,r.text; uid=r.json()['id']
 u=browser(); login(u,'tobeoff','Valid-pass-123')
 assert c.patch(f'/api/users/{uid}',headers=h,json={'active':False}).status_code==200
 assert u.post('/api/auth/refresh',headers=RH).status_code==401

def test_switch_company_rotates_refresh_cookie():
 c=browser(); r=login(c); old=c.cookies.get('abtin_rt'); me=c.get('/api/me',headers=H(r)).json()
 cid=me['company']['id']
 r2=c.post(f'/api/auth/switch-company?company_id={cid}',headers=H(r)); assert r2.status_code==200,r2.text
 assert c.cookies.get('abtin_rt')!=old
 other=browser(); other.cookies.set('abtin_rt',old,path='/api')
 assert other.post('/api/auth/refresh',headers=RH).status_code==401
