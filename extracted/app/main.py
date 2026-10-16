from __future__ import annotations
import asyncio
from importlib import import_module
import logging
from contextlib import asynccontextmanager
import os
import time
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from app.core.bootstrap import seed
from app.core import errors,idempotency,metrics,ratelimit
from app.core.config import DB_URL,REMINDER_INTERVAL_SECONDS,cors_origins,mobile,web
from app.core.database import Base,SessionLocal
from app.core.security import ALL_PERMS,OPEN_PATHS,PUBLIC_PATHS,ensure_templates,required_perm
from app.models import Company,Invoice  # noqa: F401
from app.services.accounting import backfill_ledger,set_invoice_status
from app.modules import system
from app.modules import auth_org
from app.modules import crm
from app.modules import catalog
from app.modules import inventory
from app.modules import sales
from app.modules import purchasing
from app.modules import delivery
from app.modules import field
from app.modules import automation
from app.modules import finance
from app.modules import banking
from app.modules import hr
from app.modules import platform
from app.modules import sync
from app.modules import importer
from app.modules import gps
from app.modules import reports
from app.modules import ceo
from app.modules import notify as notify_mod
from app.modules import search as search_mod
from app.modules import files as files_mod
from app.modules import contracts
from app.modules import integrations

def _reminders_once():
 with SessionLocal() as s:
  n=automation.run_reminders(s)
  try: gps.purge_gps(s)
  except Exception: s.rollback();logging.getLogger('abtin').exception('gps purge failed')
  try:
   from app.services.notify import dispatch_pending,run_alerts
   run_alerts(s);dispatch_pending(s)
  except Exception: s.rollback();logging.getLogger('abtin').exception('notification job failed')
  try: reports.purge_jobs(s)
  except Exception: s.rollback();logging.getLogger('abtin').exception('report job purge failed')
  try:
   from app.services.webhooks import dispatch_webhooks,purge_deliveries
   dispatch_webhooks(s);purge_deliveries(s);idempotency.purge(s)
  except Exception: s.rollback();logging.getLogger('abtin').exception('webhook/idempotency job failed')
  return n
async def _reminder_loop():
 while True:
  await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
  try: await run_in_threadpool(_reminders_once)
  except Exception: logging.getLogger('abtin').exception('reminder job failed')
@asynccontextmanager
async def lifespan(_app):
 try:
  with SessionLocal() as s0: reports.fail_orphan_jobs(s0)
 except Exception: logging.getLogger('abtin').exception('orphan report jobs cleanup failed')
 task=asyncio.create_task(_reminder_loop()) if REMINDER_INTERVAL_SECONDS>0 else None
 try: yield
 finally:
  if task: task.cancel()
DOCS_ON=os.getenv('API_DOCS_ENABLED','1')=='1'
API_DESC="""API نسخه‌ی ۱ سامانه‌ی توزیع آبتین. همه‌ی مسیرها زیر `/api/v1` هستند (`/api/...` بدون نسخه معادل v1 است و برای سازگاری می‌ماند).

**احراز هویت:** `Authorization: Bearer <token>` (ورود با `/auth/login`) یا کلید API با هدر `X-API-Key: abk_...`.
**خطا:** همیشه `{code, message, details, request_id}`؛ `request_id` برابر هدر `X-Request-ID` پاسخ است.
**Idempotency:** هدر `Idempotency-Key` روی POST/PUT/PATCH/DELETE؛ تکرار با همان کلید و بدنه، پاسخ اول را بازمی‌گرداند (`Idempotency-Replayed: true`).
**صفحه‌بندی:** `?limit=&offset=` و هدرهای `X-Total-Count`، `X-Limit`، `X-Offset`.
**Rate limit:** هدرهای `X-RateLimit-*`؛ در صورت عبور، ۴۲۹ با `Retry-After`."""
app=FastAPI(lifespan=lifespan,title='Abtin Distribution Suite API',version='3.0.0',description=API_DESC,docs_url=None,redoc_url=None,openapi_url=None)
errors.install(app)
def _openapi():
 if app.openapi_schema: return app.openapi_schema
 sch=get_openapi(title=app.title,version='1.0.0',description=app.description,routes=app.routes)
 paths={}
 for p,ops in sch['paths'].items():
  np='/api/v1'+p[4:] if p.startswith('/api/') else p
  for op in ops.values():
   if isinstance(op,dict) and p.startswith('/api/'): op['tags']=[p.split('/')[2]]
  paths[np]=ops
 sch['paths']=paths
 sch.setdefault('components',{}).setdefault('securitySchemes',{}).update({'bearerAuth':{'type':'http','scheme':'bearer','description':'توکن ورود'},'apiKeyAuth':{'type':'apiKey','in':'header','name':'X-API-Key','description':'کلید API یکپارچه‌سازی'}})
 sch['security']=[{'bearerAuth':[]},{'apiKeyAuth':[]}]
 sch['servers']=[{'url':'/'}]
 app.openapi_schema=sch;return sch
app.openapi=_openapi
if DOCS_ON:
 @app.get('/api/openapi.json',include_in_schema=False)
 def openapi_json(): return JSONResponse(app.openapi())
 @app.get('/docs',include_in_schema=False)
 def docs_page(): return get_swagger_ui_html(openapi_url='/api/v1/openapi.json',title=app.title+' — مستندات',swagger_favicon_url='data:,',swagger_js_url='https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.min.js',swagger_css_url='https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.min.css')
@app.middleware('http')
async def security_headers(request:Request,call_next):
 resp=await call_next(request)
 resp.headers.setdefault('Content-Security-Policy',"default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
 resp.headers.setdefault('X-Content-Type-Options','nosniff');resp.headers.setdefault('X-Frame-Options','DENY');resp.headers.setdefault('Referrer-Policy','same-origin')
 resp.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=(self)')
 if request.headers.get('x-forwarded-proto','').split(',')[0].strip()=='https' or request.url.scheme=='https': resp.headers.setdefault('Strict-Transport-Security','max-age=31536000; includeSubDomains')
 if request.url.path.startswith('/api/'): resp.headers.setdefault('Cache-Control','no-store')
 return resp
@app.middleware('http')
async def metrics_mw(request:Request,call_next):
 t=time.perf_counter()
 try: resp=await call_next(request)
 except Exception:
  metrics.observe(request.method,'unmatched',500,time.perf_counter()-t);raise
 r=request.scope.get('route');metrics.observe(request.method,getattr(r,'path','unmatched'),resp.status_code,time.perf_counter()-t)
 return resp
app.middleware('http')(idempotency.middleware)
@app.middleware('http')
async def rate_limit(request:Request,call_next):
 hit=ratelimit.check(request)
 if hit: return errors.error_response(request,429,'تعداد درخواست‌ها از حد مجاز گذشته است؛ کمی بعد دوباره تلاش کنید','rate_limited',headers={'Retry-After':str(hit[1]),'X-RateLimit-Limit':str(hit[0]),'X-RateLimit-Remaining':'0'})
 resp=await call_next(request)
 for k,v in (getattr(request.state,'rl',None) or {}).items(): resp.headers[k]=v
 return resp
@app.middleware('http')
async def request_context(request:Request,call_next):
 """شناسه‌ی درخواست + نسخه‌بندی: `/api/v1/x` به `/api/x` بازنویسی می‌شود تا مجوزها/تست‌ها/مسیرهای قبلی دست‌نخورده بمانند"""
 rid=errors.request_id(request);p=request.scope['path']
 from app.core.common import REQ_CTX
 from app.core.ratelimit import client_ip
 REQ_CTX.set({'ip':client_ip(request)[:64],'request_id':rid})
 if p=='/api/v1' or p.startswith('/api/v1/'):
  request.scope['path']='/api'+p[7:];request.scope['raw_path']=request.scope['path'].encode();request.state.api_version='v1'
 resp=await call_next(request);resp.headers['X-Request-ID']=rid
 if p.startswith('/api/'): resp.headers.setdefault('X-API-Version','1')
 return resp
if cors_origins(): app.add_middleware(CORSMiddleware,allow_origins=cors_origins(),allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','X-API-Key','Idempotency-Key','X-Request-ID'],expose_headers=['X-Request-ID','X-Total-Count','X-Limit','X-Offset','X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset','Retry-After','Idempotency-Replayed'],allow_credentials=False,max_age=600)
app.mount('/web',StaticFiles(directory=web,html=True),name='web')
app.mount('/mobile',StaticFiles(directory=mobile,html=True),name='mobile')
_fe=os.path.join(os.path.dirname(web),'frontend','dist')
if os.path.isdir(_fe): app.mount('/app',StaticFiles(directory=_fe,html=True),name='app')
for _m in (system,auth_org,crm,catalog,inventory,sales,purchasing,delivery,field,automation,finance,banking,hr,platform,sync,importer,gps,reports,ceo,notify_mod,search_mod,files_mod,contracts,integrations,): app.include_router(import_module(f'{_m.__name__}.router').router)
seed()
with SessionLocal() as _s:
 for _c in _s.scalars(select(Company)).all(): ensure_templates(_s,_c.id)
backfill_ledger()
