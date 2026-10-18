from __future__ import annotations
import hmac
import os
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import text
from app.core.config import utcnow, web
from app.core import metrics
from app.core.database import SessionLocal

VERSION='3.0.0'

def root():
 return FileResponse(os.path.join(web, 'index.html'))

def health():
 return {'ok': True, 'service': 'abtin-distribution', 'version': VERSION, 'api_version': 'v1', 'time': utcnow().isoformat()}

def ready():
 """آماده‌به‌کار بودن (اتصال دیتابیس) برای load balancer / orchestrator"""
 try:
  with SessionLocal() as s: s.execute(text('SELECT 1'))
 except Exception: return JSONResponse({'ok':False,'db':False},status_code=503)
 return {'ok':True,'db':True}

def metrics_endpoint(request: Request):
 """متریک Prometheus؛ فقط وقتی METRICS_TOKEN تنظیم شده و هدر Authorization: Bearer <token> درست باشد (وگرنه ۴۰۴)"""
 tok=os.getenv('METRICS_TOKEN','')
 got=request.headers.get('authorization','')[7:] if request.headers.get('authorization','').lower().startswith('bearer ') else ''
 if not tok or not hmac.compare_digest(got.encode(),tok.encode()): return JSONResponse({'detail':'Not Found'},status_code=404)
 return PlainTextResponse(metrics.render(),media_type='text/plain; version=0.0.4')
