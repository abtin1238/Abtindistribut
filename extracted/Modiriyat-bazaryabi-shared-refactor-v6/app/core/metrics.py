"""متریک Prometheus بدون وابستگی خارجی. شمارنده‌ی درخواست + هیستوگرام تأخیر.
برچسب مسیر = الگوی مسیر (route.path) تا کاردینالیتی کنترل‌شده بماند؛ مسیر ناشناخته = «unmatched»."""
from __future__ import annotations
import threading
import time

BUCKETS=(0.025,0.05,0.1,0.25,0.5,1.0,2.5,5.0,10.0)
_lock=threading.Lock()
_started=time.time()
_req:dict[tuple[str,str,str],int]={}
_hist:dict[tuple[str,str],list[float]]={}   # (method,path) -> [bucket counts..., +Inf, sum]

def _esc(v:str)->str: return v.replace('\\','\\\\').replace('"','\\"').replace('\n',' ')

def observe(method:str,path:str,status:int,seconds:float)->None:
 cls=f'{status//100}xx'
 with _lock:
  _req[(method,path,cls)]=_req.get((method,path,cls),0)+1
  h=_hist.setdefault((method,path),[0.0]*(len(BUCKETS)+2))
  for i,b in enumerate(BUCKETS):
   if seconds<=b: h[i]+=1
  h[len(BUCKETS)]+=1;h[len(BUCKETS)+1]+=seconds

def render()->str:
 out=['# HELP abtin_http_requests_total Total HTTP requests','# TYPE abtin_http_requests_total counter']
 with _lock:
  for (m,p,c),n in sorted(_req.items()): out.append(f'abtin_http_requests_total{{method="{_esc(m)}",path="{_esc(p)}",status_class="{c}"}} {n}')
  out+=['# HELP abtin_http_request_duration_seconds Request latency','# TYPE abtin_http_request_duration_seconds histogram']
  for (m,p),h in sorted(_hist.items()):
   lab=f'method="{_esc(m)}",path="{_esc(p)}"'
   for i,b in enumerate(BUCKETS): out.append(f'abtin_http_request_duration_seconds_bucket{{{lab},le="{b}"}} {int(h[i])}')
   out.append(f'abtin_http_request_duration_seconds_bucket{{{lab},le="+Inf"}} {int(h[len(BUCKETS)])}')
   out.append(f'abtin_http_request_duration_seconds_sum{{{lab}}} {h[len(BUCKETS)+1]:.6f}')
   out.append(f'abtin_http_request_duration_seconds_count{{{lab}}} {int(h[len(BUCKETS)])}')
 out+=['# HELP abtin_process_uptime_seconds Seconds since process start','# TYPE abtin_process_uptime_seconds gauge',f'abtin_process_uptime_seconds {time.time()-_started:.0f}']
 return '\n'.join(out)+'\n'

def reset()->None:
 with _lock: _req.clear();_hist.clear()
