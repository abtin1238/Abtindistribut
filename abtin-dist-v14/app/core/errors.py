"""فرمت خطای واحد: {code,message,details,request_id} (+ `detail` برای سازگاری با کلاینت‌های قبلی)"""
from __future__ import annotations
import logging
import re
import uuid
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log=logging.getLogger('abtin')
RID_RE=re.compile(r'^[A-Za-z0-9._-]{8,64}$')
CODES={400:'bad_request',401:'unauthorized',403:'forbidden',404:'not_found',405:'method_not_allowed',409:'conflict',410:'gone',413:'payload_too_large',415:'unsupported_media_type',422:'validation_error',429:'rate_limited',503:'unavailable'}
def request_id(request:Request)->str:
 rid=getattr(request.state,'request_id',None)
 if not rid:
  h=request.headers.get('x-request-id','')
  rid=h if RID_RE.match(h) else uuid.uuid4().hex;request.state.request_id=rid
 return rid
def error_body(request,status,message,code=None,details=None,detail=None):
 return {'code':code or CODES.get(status,'error' if status<500 else 'internal_error'),'message':message,'details':details,'request_id':request_id(request),'detail':message if detail is None else detail}
def error_response(request,status,message,code=None,details=None,detail=None,headers=None):
 h={'X-Request-ID':request_id(request),**(headers or {})}
 return JSONResponse(error_body(request,status,message,code,details,detail),status_code=status,headers=h)
def _loc(e): return '.'.join(str(x) for x in e.get('loc',()) if x!='body')
def install(app:FastAPI):
 @app.exception_handler(StarletteHTTPException)
 async def _http(request:Request,exc:StarletteHTTPException):
  d=exc.detail
  if isinstance(d,dict) and 'message' in d: return error_response(request,exc.status_code,str(d['message']),d.get('code'),d.get('details'),headers=exc.headers)
  return error_response(request,exc.status_code,d if isinstance(d,str) else str(d),headers=exc.headers)
 @app.exception_handler(RequestValidationError)
 async def _val(request:Request,exc:RequestValidationError):
  items=[{'field':_loc(e),'message':e.get('msg',''),'type':e.get('type','')} for e in exc.errors()]
  return error_response(request,422,'داده‌ی ورودی نامعتبر است',details=items,detail=[{'loc':list(e.get('loc',())),'msg':e.get('msg',''),'type':e.get('type','')} for e in exc.errors()])
 @app.exception_handler(Exception)
 async def _any(request:Request,exc:Exception):
  rid=request_id(request);log.exception('unhandled error request_id=%s %s %s',rid,request.method,request.url.path)
  return error_response(request,500,'خطای داخلی سرور؛ کد پیگیری: '+rid,'internal_error')
