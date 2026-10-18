"""Rate limit پنجره‌ی لغزان در حافظه‌ی هر پروسه.
⚠️ با چند worker هر پروسه شمارنده‌ی خودش را دارد؛ برای سقف دقیق سراسری باید به Redis منتقل شود (فعلاً سقف مؤثر = N × سقف)."""
from __future__ import annotations
import hashlib
import os
import threading
import time
from collections import deque
from fastapi import Request
from app.core.config import env_int

class Limiter:
 def __init__(self): self.h={};self.lock=threading.Lock();self.gc_at=0.0
 def hit(self,key,limit,window=60,now=None):
  """(مجاز؟، باقی‌مانده، ثانیه تا آزادشدن)"""
  now=time.monotonic() if now is None else now
  with self.lock:
   if now-self.gc_at>window:
    self.gc_at=now
    for k in [k for k,q in self.h.items() if not q or now-q[-1]>window]: self.h.pop(k,None)
   q=self.h.setdefault(key,deque())
   while q and now-q[0]>=window: q.popleft()
   if len(q)>=limit: return False,0,max(1,int(window-(now-q[0]))+1)
   q.append(now);return True,limit-len(q),max(1,int(window-(now-q[0])))
 def reset(self):
  with self.lock: self.h.clear()
LIMITER=Limiter()
def client_ip(request:Request):
 if os.getenv('TRUST_PROXY','0')=='1':
  f=request.headers.get('x-forwarded-for','').split(',')[0].strip()
  if f: return f
 return request.client.host if request.client else 'unknown'
def principal(request:Request):
 k=request.headers.get('x-api-key') or request.headers.get('authorization')
 return 'k:'+hashlib.sha256(k.encode()).hexdigest()[:20] if k else 'ip:'+client_ip(request)
def check(request:Request):
 """None اگر مجاز؛ وگرنه (limit,retry_after) برای پاسخ ۴۲۹. هدرهای RateLimit در request.state.rl ذخیره می‌شوند."""
 path=request.url.path
 if not path.startswith('/api/') or path in ('/api/health','/api/ready'): return None
 if path in ('/api/auth/login','/api/auth/refresh') and request.method=='POST':
  rf=path.endswith('/refresh'); lim=env_int('RATE_LIMIT_REFRESH_PER_MIN',120) if rf else env_int('RATE_LIMIT_LOGIN_PER_MIN',30)
  if lim>0:
   ok,_,ra=LIMITER.hit(('refresh:' if rf else 'login:')+client_ip(request),lim)
   if not ok: return lim,ra
 lim=env_int('RATE_LIMIT_PER_MIN',600)
 if lim<=0: return None
 ok,rem,reset=LIMITER.hit(principal(request),lim)
 request.state.rl={'X-RateLimit-Limit':str(lim),'X-RateLimit-Remaining':str(rem),'X-RateLimit-Reset':str(reset)}
 return None if ok else (lim,reset)
