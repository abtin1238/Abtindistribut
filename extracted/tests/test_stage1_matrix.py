"""ماتریس دسترسی: هر مسیر API بدون توکن ۴۰۱ می‌دهد (به‌جز عمومی‌ها)، با نقش کم‌دسترسی مسیرهای مدیریتی ۴۰۳، و Audit تغییرناپذیر است و IP ثبت می‌کند."""
import os,re
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s1mx.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import PUBLIC_PATHS,required_perm,has_perm

client=TestClient(app,raise_server_exceptions=False)
STRICTER_BY_DESIGN={('POST','/api/automation/run-reminders')}  # علاوه بر مجوز، data.all می‌خواهد (اجرای سراسری شرکت)
PUBLIC_EXACT={'/api/auth/login','/api/auth/refresh','/api/health','/api/ready'}

def _flat(rs):
 for r in rs:
  if isinstance(r,APIRoute): yield r
  elif hasattr(r,'routes'): yield from _flat(r.routes)
  elif hasattr(r,'original_router'): yield from _flat(r.original_router.routes)
def routes():
 out=set()
 for r in _flat(app.routes):
  if r.path.startswith('/api/'):
   for m in r.methods-{'HEAD','OPTIONS'}: out.add((m,r.path))
 return sorted(out)

def fill(p): return re.sub(r'\{[^}]+\}','1',p)

def is_public(path): return path.startswith(PUBLIC_PATHS)

def admin():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_every_api_route_is_registered_and_enumerated():
 assert len(routes())>150

def test_all_non_public_routes_reject_anonymous():
 bad=[]
 for m,p in routes():
  if is_public(fill(p)) or p in PUBLIC_EXACT: continue
  r=client.request(m,fill(p))
  if r.status_code!=401: bad.append((m,p,r.status_code))
 assert not bad,bad

def test_unknown_api_path_defaults_to_admin_write():
 assert required_perm('GET','/api/zzz-new-module')=='admin.write'

def test_every_route_maps_to_a_known_permission_or_is_open():
 from app.core.security import ALL_PERMS,MODS
 unknown=[]
 for m,p in routes():
  perm=required_perm(m,fill(p))
  if perm and perm not in ALL_PERMS and perm.split('.')[0] not in MODS: unknown.append((m,p,perm))
 assert not unknown,unknown

def test_low_privilege_role_blocked_from_admin_endpoints():
 h=admin(); client.post('/api/roles/templates',headers=h)
 rid=next(r['id'] for r in client.get('/api/roles',headers=h).json() if r['name']=='فروشنده')
 assert client.post('/api/users',headers=h,json={'username':'mx_seller','password':'Matrix-pass-123','name':'x','role_id':rid}).status_code==200
 r=client.post('/api/auth/login',json={'username':'mx_seller','password':'Matrix-pass-123'}); sh={'Authorization':'Bearer '+r.json()['token']}
 role=next(x for x in client.get('/api/roles',headers=h).json() if x['id']==rid)
 denied=[];allowed_wrongly=[]
 for m,p in routes():
  perm=required_perm(m,fill(p))
  if not perm or is_public(fill(p)): continue
  should=has_perm(type('R',(),{'permissions':role['permissions']})(),perm)
  code=client.request(m,fill(p),headers=sh).status_code
  if not should and code!=403: allowed_wrongly.append((m,p,perm,code))
  if should and code==403 and (m,p) not in STRICTER_BY_DESIGN: denied.append((m,p,perm))
 assert not allowed_wrongly,allowed_wrongly
 assert not denied,denied

def test_audit_records_ip_and_request_id_and_is_immutable():
 from app.core.database import SessionLocal
 from app.models import Audit
 from sqlalchemy import select
 c=TestClient(app); r=c.post('/api/auth/login',json={'username':'admin','password':'test-password'},headers={'X-Request-ID':'matrix-req-1'}); assert r.status_code==200
 with SessionLocal() as s:
  a=s.scalars(select(Audit).where(Audit.action=='login').order_by(Audit.id.desc())).first()
  assert a.request_id=='matrix-req-1' and a.ip
  a.action='tampered'
  with pytest.raises(RuntimeError): s.flush()
  s.rollback()
  s.delete(s.get(Audit,a.id))
  with pytest.raises(RuntimeError): s.flush()
  s.rollback()
