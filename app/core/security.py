from __future__ import annotations
import hashlib
import hmac
import re
import secrets
from fastapi import Depends,HTTPException,Header,Request
from sqlalchemy import or_,select
from sqlalchemy.orm import Session
from typing import Optional
from app.core.config import utcnow
from app.core.database import db
from app.models import ApiKey,Delivery,Membership,Order,Role,SessionToken,User,Warehouse

PERM_MOD={'/api/customers':'crm','/api/leads':'automation','/api/tasks':'automation','/api/proposals':'automation','/api/targets':'automation','/api/automation':'automation','/api/products':'catalog','/api/product-units':'catalog','/api/pricing':'pricing','/api/campaigns':'pricing','/api/brands':'catalog','/api/categories':'catalog','/api/price-rules':'pricing','/api/warehouses':'inventory','/api/stock':'inventory','/api/orders':'sales','/api/sales-returns':'sales','/api/invoices':'sales','/api/suppliers':'purchase','/api/purchases':'purchase','/api/deliveries':'delivery','/api/visits':'visit','/api/visit-plans':'visit','/api/payments':'finance','/api/fiscal':'finance','/api/journal':'finance','/api/accounts':'finance','/api/checks':'finance','/api/bank-accounts':'finance','/api/bank-transfers':'finance','/api/chequebooks':'finance','/api/employees':'hr','/api/attendance':'hr','/api/leaves':'hr','/api/shifts':'hr','/api/payroll':'hr','/api/users':'admin','/api/roles':'admin','/api/memberships':'admin','/api/organizations':'admin','/api/audit':'admin','/api/settings':'settings','/api/documents':'files','/api/contracts':'files','/api/reports':'reports','/api/import':'import','/api/gps':'gps','/api/geofences':'gps','/api/ceo':'reports','/api/api-keys':'admin','/api/webhooks':'admin','/api/webhook-deliveries':'admin'}
OPEN_PATHS=('/api/me','/api/notifications','/api/push','/api/dashboard','/api/search','/api/sync','/api/auth','/api/permissions')
PUBLIC_PATHS=('/api/auth/login','/api/auth/refresh','/api/brand/logo/','/api/health','/api/ready','/api/openapi.json')
FIN_REPORTS=('/api/reports/trial-balance','/api/reports/profit-loss','/api/reports/balance-sheet','/api/reports/general-ledger','/api/reports/aging')
LEDGER_RE=re.compile(r'^/api/customers/\d+/ledger$')
def required_perm(method,path):
 if path=='/api/payments' and method=='POST': return 'finance.collect'
 if path in ('/api/gps/points','/api/gps/config'): return 'gps.record'
 if method=='GET' and path=='/api/gps/customers': return 'crm.read'
 if method=='POST' and path.startswith('/api/deliveries/') and (path.endswith('/collect') or path.endswith('/photo')): return 'delivery.update'
 if method=='POST' and path=='/api/deliveries/bulk-assign': return 'delivery.assign'
 if path.startswith(PUBLIC_PATHS): return None
 if path.startswith('/api/reports/jobs') and method=='POST': return 'reports.read'
 if path.startswith('/api/dashboard/'): return 'sales.read'
 if path.startswith(FIN_REPORTS) or LEDGER_RE.match(path): return 'finance.read'
 if any(path==o or path.startswith(o+'/') for o in OPEN_PATHS) or (method=='GET' and path in ('/api/settings/brand','/api/settings/theme')): return None
 for pre,mod in PERM_MOD.items():
  if path.startswith(pre):
   if path.endswith('/approve') or path.endswith('/cancel') or path.endswith('/reverse') or path.endswith('/close') or path.endswith('/reject') or path.endswith('/post') and path.startswith('/api/payroll') or path.endswith('/pay') and path.startswith('/api/payroll') or path.endswith('/endorse') or path.endswith('/reopen') or path.endswith('/return'): return mod+'.approve'
   if path.endswith('/assign-delivery'): return 'delivery.assign'
   if mod=='delivery' and method=='PATCH': return 'delivery.update'
   return mod+('.read' if method=='GET' else '.write')
 if path.startswith('/api/'): return 'admin.write'
def has_perm(r,p):
 ps=(r.permissions if r else None) or []
 mo,_,a=p.partition('.')
 return '*' in ps or p in ps or mo+'.*' in ps or (a in ('read','collect') and mo+'.write' in ps)
def hashpw(p,s=None):
 s=s or secrets.token_hex(16); return s+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),210000).hex()
def checkpw(p,h):
 try:s,d=h.split('$',1); return hmac.compare_digest(hashpw(p,s).split('$',1)[1],d)
 except:return False
def _api_key_ctx(request,s,raw):
 """کلید API: `abk_<8hex>_<secret>` از هدر X-API-Key یا Authorization: Bearer abk_…؛ فقط هش ذخیره می‌شود"""
 bad=HTTPException(401,'کلید API نامعتبر است')
 parts=raw.split('_',2)
 if len(parts)!=3 or parts[0]!='abk' or len(parts[1])!=8: raise bad
 k=s.scalar(select(ApiKey).where(ApiKey.prefix=='abk_'+parts[1]))
 if not k or not hmac.compare_digest(hashlib.sha256(parts[2].encode()).hexdigest(),k.key_hash): raise bad
 now=utcnow()
 if k.revoked_at or (k.expires_at and k.expires_at<now): raise HTTPException(401,'کلید API باطل یا منقضی شده است')
 u=s.get(User,k.created_by);r=s.get(Role,k.role_id)
 if not u or not u.active or not r or r.company_id!=k.company_id: raise HTTPException(401,'کلید API معتبر نیست')
 if not k.last_used_at or (now-k.last_used_at).total_seconds()>60: k.last_used_at=now;s.commit()
 request.state.api_key_id=k.id
 return u,k.company_id,r
def current(request:Request,auth:Optional[str]=Header(None,alias='Authorization'),x_api_key:Optional[str]=Header(None,alias='X-API-Key'),s:Session=Depends(db)):
 raw=x_api_key or (auth[7:] if auth and auth.startswith('Bearer abk_') else None)
 if raw: u,cid,r=_api_key_ctx(request,s,raw)
 else:
  if not auth or not auth.startswith('Bearer '): raise HTTPException(401,'احراز هویت لازم است')
  x=s.get(SessionToken,auth[7:])
  if not x or x.expires_at<utcnow(): raise HTTPException(401,'نشست منقضی شده است')
  u=s.get(User,x.user_id); r=s.get(Role,u.role_id) if u else None
  if not u or not u.active: raise HTTPException(401,'کاربر غیرفعال است')
  cid=x.company_id
 p=required_perm(request.method,request.url.path)
 if p and not has_perm(r,p): raise HTTPException(403,'دسترسی کافی نیست')
 return u,cid,r
def need(ctx,permission):
 if '*' in (ctx[2].permissions or []): return
 if permission not in (ctx[2].permissions or []): raise HTTPException(403,'دسترسی کافی نیست')
def wh_scope(s,ctx):
 # None = بدون محدودیت؛ وگرنه مجموعه‌ی انبارهای مجاز (انبارهای شعبه‌ی کاربر + انبارهای بدون شعبه)
 u,cid,r=ctx
 if has_all(r): return None
 bs=[m for m in s.scalars(select(Membership.branch_id).where(Membership.user_id==u.id,Membership.company_id==cid))]
 if not bs or None in bs: return None
 return set(s.scalars(select(Warehouse.id).where(Warehouse.company_id==cid,or_(Warehouse.branch_id.in_(bs),Warehouse.branch_id==None))))
def wh_check(s,ctx,wid):
 sc=wh_scope(s,ctx)
 if sc is not None and wid not in sc: raise HTTPException(404,'انبار یافت نشد')
MODS=set(PERM_MOD.values())
ALL_PERMS={f'{a}.{b}' for a in MODS for b in ('read','write')}|{'sales.approve','inventory.approve','finance.approve','delivery.assign','delivery.update','delivery.read.all','finance.collect','data.all','gps.record'}
def has_all(r): ps=(r.permissions if r else None) or [];return '*' in ps or 'data.all' in ps
def own_orders(u): return or_(Order.seller_id==u.id,Order.id.in_(select(Delivery.order_id).where(Delivery.driver_id==u.id)))
def granted(r,perms): return all(has_perm(r,p) for p in perms)
def check_codes(perms):
 bad=[p for p in perms if p!='*' and p not in ALL_PERMS and not (p.endswith('.*') and p[:-2] in MODS)]
 if bad: raise HTTPException(400,'کد دسترسی نامعتبر: '+', '.join(bad))
TEMPLATES={'مدیر شرکت':sorted(ALL_PERMS),
'مدیر فروش':['gps.read','automation.write','crm.write','catalog.read','pricing.read','inventory.read','sales.write','sales.approve','delivery.assign','delivery.read','delivery.read.all','visit.write','reports.read','files.write','data.all'],
'فروشنده':['automation.write','crm.write','catalog.read','pricing.read','inventory.read','sales.write','files.write'],
'حسابدار':['finance.write','finance.approve','sales.read','purchase.read','crm.read','reports.read','hr.read','files.write','data.all'],
'انباردار':['inventory.write','catalog.read','purchase.write','delivery.read','delivery.read.all','sales.read','data.all'],
'بازاریاب':['gps.record','automation.write','crm.read','catalog.read','pricing.read','inventory.read','sales.write','visit.write','finance.collect','files.write'],
'مأمور پخش':['gps.record','delivery.read','delivery.update','sales.read','finance.collect','files.write']}
def ensure_templates(s,cid):
 have={x.name for x in s.scalars(select(Role).where(Role.company_id==cid))}
 for n,p in TEMPLATES.items():
  if n not in have: s.add(Role(company_id=cid,name=n,permissions=p))
 s.commit()
