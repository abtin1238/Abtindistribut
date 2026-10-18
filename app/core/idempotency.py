"""Idempotency-Key برای POST/PUT/PATCH/DELETE: تکرار همان درخواست (همان کلید و بدنه) پاسخ ذخیره‌شده را بازمی‌گرداند و عملیات دوباره اجرا نمی‌شود.
دامنه‌ی کلید = توکن/کلید API فرستنده (هش)؛ بنابراین با ورود دوباره (توکن تازه) کلیدها جدا هستند. برای صف آفلاین از `/api/sync` استفاده شود (آیدی رویداد خودش یکتاست)."""
from __future__ import annotations
import hashlib
import re
from datetime import timedelta
from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy import delete,select
from sqlalchemy.exc import IntegrityError
from app.core.config import utcnow
from app.core.database import SessionLocal
from app.core.errors import error_response
from app.models import IdempotencyRecord

KEY_RE=re.compile(r'^[A-Za-z0-9_.:-]{8,120}$')
MAX_BODY=1024*1024
STALE=timedelta(minutes=5)
RETENTION=timedelta(hours=48)
UNSAFE={'POST','PUT','PATCH','DELETE'}
def applies(request:Request):
 return request.method in UNSAFE and request.url.path.startswith('/api/') and not request.url.path.startswith('/api/auth/') and 'idempotency-key' in request.headers
def scope_of(request:Request):
 cred=request.headers.get('x-api-key') or request.headers.get('authorization')
 return hashlib.sha256(cred.encode()).hexdigest()[:40] if cred else None
def fingerprint(request:Request,body:bytes):
 h=hashlib.sha256();h.update(f'{request.method}\n{request.url.path}\n{request.url.query}\n'.encode());h.update(body);return h.hexdigest()
def begin(scope,key,fp):
 """('new',None) | ('replay',rec) | ('mismatch',None) | ('busy',None)"""
 with SessionLocal() as s:
  for _ in range(3):
   try:
    s.add(IdempotencyRecord(scope=scope,key=key,fingerprint=fp,status='processing'));s.commit();return 'new',None
   except IntegrityError:
    s.rollback();r=s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.scope==scope,IdempotencyRecord.key==key))
    if r is None: continue
    if r.fingerprint!=fp: return 'mismatch',None
    if r.status=='done': return 'replay',(r.response_status,r.response_body or '',r.response_type or 'application/json')
    if utcnow()-r.created_at>STALE:   # پروسه‌ی قبلی وسط کار مرده است
     s.execute(delete(IdempotencyRecord).where(IdempotencyRecord.id==r.id,IdempotencyRecord.status=='processing'));s.commit();continue
    return 'busy',None
  return 'busy',None
def finish(scope,key,status,body,ctype):
 """پاسخ‌های موقتی (۵xx، ۴۰۱/۴۰۳/۴۲۹) یا بزرگ ذخیره نمی‌شوند تا کلاینت بتواند دوباره تلاش کند."""
 with SessionLocal() as s:
  r=s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.scope==scope,IdempotencyRecord.key==key))
  if not r: return
  text=None
  if status<500 and status not in (401,403,429) and len(body)<=MAX_BODY:
   try: text=body.decode('utf-8')
   except UnicodeDecodeError: text=None
  if text is None: s.delete(r)
  else: r.status='done';r.response_status=status;r.response_body=text;r.response_type=ctype[:100]
  s.commit()
def purge(s):
 n=s.execute(delete(IdempotencyRecord).where(IdempotencyRecord.created_at<utcnow()-RETENTION)).rowcount;s.commit();return n
async def middleware(request:Request,call_next):
 if not applies(request): return await call_next(request)
 key=request.headers['idempotency-key'];scope=scope_of(request)
 if not scope: return await call_next(request)   # بدون اعتبارنامه: همان خطای ۴۰۱ معمول
 if not KEY_RE.match(key): return error_response(request,400,'Idempotency-Key نامعتبر است (۸ تا ۱۲۰ نویسه‌ی حرف/عدد/._:-)','invalid_idempotency_key')
 body=await request.body();fp=fingerprint(request,body)
 st,rec=await run_in_threadpool(begin,scope,key,fp)
 if st=='mismatch': return error_response(request,422,'این Idempotency-Key قبلاً با درخواست دیگری استفاده شده است','idempotency_key_reuse')
 if st=='busy': return error_response(request,409,'درخواست قبلی با همین کلید هنوز در حال پردازش است','idempotency_in_progress',headers={'Retry-After':'1'})
 if st=='replay':
  status,text,ctype=rec
  return Response(content=text,status_code=status,media_type=ctype,headers={'Idempotency-Replayed':'true'})
 try:
  resp=await call_next(request)
  chunks=[c async for c in resp.body_iterator];data=b''.join(chunks)
 except BaseException:
  await run_in_threadpool(finish,scope,key,500,b'','')
  raise
 await run_in_threadpool(finish,scope,key,resp.status_code,data,resp.headers.get('content-type','application/json'))
 headers={k:v for k,v in resp.headers.items() if k.lower() not in ('content-length',)}
 return Response(content=data,status_code=resp.status_code,headers=headers,media_type=resp.headers.get('content-type'))
