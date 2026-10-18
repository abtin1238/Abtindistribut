"""وبهوک خروجی: رویداد → ردیف pending → ارسال امضاشده (HMAC-SHA256) با تلاش مجدد پلکانی.
امضا: هدر `X-Abtin-Signature: v1=<hex>` روی رشته‌ی `"{timestamp}.{body}"` با secret اندپوینت؛ زمان در `X-Abtin-Timestamp`.
گیرنده باید |now - timestamp| را (مثلاً ۵ دقیقه) بررسی کند تا replay رد شود."""
from __future__ import annotations
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import time
import urllib.error
import urllib.request
import uuid
from datetime import timedelta
from urllib.parse import urlsplit
from sqlalchemy import select,update
from app.core.config import utcnow
from app.models import WebhookDelivery,WebhookEndpoint

log=logging.getLogger('abtin')
EVENTS={'order.created':'سفارش جدید','invoice.approved':'تأیید فاکتور','delivery.created':'ماموریت پخش جدید','delivery.delivered':'تحویل موفق','delivery.failed':'عدم تحویل','stock.low':'کمبود موجودی','check.due':'سررسید چک','task.assigned':'وظیفه‌ی جدید','task.reminder':'یادآوری وظیفه/تماس','lead.followup':'پیگیری سرنخ','system.notice':'اعلان سیستمی','webhook.test':'آزمایش اتصال'}
NOTIFY_MAP={'order_new':'order.created','invoice_approved':'invoice.approved','delivery_new':'delivery.created','delivery_done':'delivery.delivered','delivery_failed':'delivery.failed','low_stock':'stock.low','check_due':'check.due','task_assigned':'task.assigned','task_reminder':'task.reminder','lead_followup':'lead.followup','system':'system.notice'}
BACKOFF=[60,300,1800,7200,43200]          # ثانیه؛ بعد از تلاش ششم → failed
MAX_ATTEMPTS=len(BACKOFF)+1
DISABLE_AFTER=30                          # شکست متوالی → اندپوینت غیرفعال
TIMEOUT=8
STALE_SENDING=timedelta(minutes=5)
class UrlRejected(ValueError): pass
def new_secret(): return 'whsec_'+secrets.token_urlsafe(32)
def check_url(url:str,resolve=True):
 """جلوگیری از SSRF: فقط https (http فقط با WEBHOOK_ALLOW_HTTP=1)، بدون userinfo، و مقصد باید آدرس عمومی باشد (WEBHOOK_ALLOW_PRIVATE=1 برای شبکه‌ی داخلی/توسعه).
 ⚠️ حل DNS هنگام ارسال دوباره بررسی می‌شود ولی بین بررسی و اتصال پنجره‌ی DNS-rebinding کوچکی می‌ماند؛ برای حذف کامل، ارسال را از طریق egress proxy انجام دهید."""
 if not isinstance(url,str) or len(url)>500: raise UrlRejected('نشانی نامعتبر است')
 try: u=urlsplit(url.strip());port=u.port
 except ValueError: raise UrlRejected('نشانی نامعتبر است')
 if u.scheme not in ('https','http') or (u.scheme=='http' and os.getenv('WEBHOOK_ALLOW_HTTP','0')!='1'): raise UrlRejected('فقط نشانی https مجاز است')
 if not u.hostname or u.username or u.password: raise UrlRejected('نشانی نامعتبر است')
 if resolve and os.getenv('WEBHOOK_ALLOW_PRIVATE','0')!='1':
  try: infos=socket.getaddrinfo(u.hostname,port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)
  except OSError: raise UrlRejected('نام میزبان قابل‌حل نیست')
  for i in infos:
   ip=ipaddress.ip_address(i[4][0].split('%')[0])
   if not ip.is_global or ip.is_multicast: raise UrlRejected('نشانی مقصد باید عمومی باشد (شبکه‌ی داخلی/لوکال مجاز نیست)')
 return url.strip()
def sign(secret:str,ts:int,body:bytes)->str: return 'v1='+hmac.new(secret.encode(),f'{ts}.'.encode()+body,hashlib.sha256).hexdigest()
def emit_event(s,cid,event,data,dedupe=None):
 """ردیف‌های pending برای اندپوینت‌های فعالِ مشترک؛ بدون commit. تعداد اندپوینت‌ها را برمی‌گرداند."""
 eid=hashlib.sha1(dedupe.encode()).hexdigest()[:32] if dedupe else uuid.uuid4().hex
 n=0
 for ep in s.scalars(select(WebhookEndpoint).where(WebhookEndpoint.company_id==cid,WebhookEndpoint.active==True)).all():
  if '*' not in (ep.events or []) and event not in (ep.events or []): continue
  if dedupe and s.scalar(select(WebhookDelivery.id).where(WebhookDelivery.endpoint_id==ep.id,WebhookDelivery.event_id==eid)): continue
  s.add(WebhookDelivery(company_id=cid,endpoint_id=ep.id,event=event,event_id=eid,payload={'id':eid,'event':event,'created_at':utcnow().isoformat()+'Z','data':data}));n+=1
 return n
def emit_from_notify(s,cid,event,title,body,entity,entity_id,dedupe):
 ev=NOTIFY_MAP.get(event)
 if not ev: return 0
 return emit_event(s,cid,ev,{'title':title,'body':body,'entity':entity,'entity_id':entity_id},dedupe)
class _NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k): return None
def http_post(url,body,headers):
 """(status_code, error_text) — هیچ ریدایرکتی دنبال نمی‌شود"""
 req=urllib.request.Request(url,data=body,headers=headers,method='POST')
 try:
  with urllib.request.build_opener(_NoRedirect).open(req,timeout=TIMEOUT) as r: return r.status,''
 except urllib.error.HTTPError as e: return e.code,f'HTTP {e.code}'
 except Exception as e: return None,(str(getattr(e,'reason',e)) or e.__class__.__name__)[:250]
def deliver_one(s,d,ep,post=None):
 """یک تلاش ارسال؛ commit خودش را انجام می‌دهد."""
 post=post or http_post;d.attempts+=1
 body=json.dumps(d.payload,ensure_ascii=False,separators=(',',':')).encode();ts=int(time.time())
 try:
  check_url(ep.url)
  code,err=post(ep.url,body,{'Content-Type':'application/json; charset=utf-8','User-Agent':'Abtin-Webhook/1','X-Abtin-Event':d.event,'X-Abtin-Event-Id':d.event_id,'X-Abtin-Delivery':str(d.id),'X-Abtin-Timestamp':str(ts),'X-Abtin-Signature':sign(ep.secret,ts,body)})
 except UrlRejected as e: code,err=None,str(e)
 d.response_code=code
 if code is not None and 200<=code<300:
  d.status='delivered';d.error='';ep.consecutive_failures=0
 else:
  d.error=(err or f'HTTP {code}')[:300];ep.consecutive_failures=(ep.consecutive_failures or 0)+1
  if d.attempts>=MAX_ATTEMPTS: d.status='failed'
  else: d.status='pending';d.next_try_at=utcnow()+timedelta(seconds=BACKOFF[d.attempts-1])
  if ep.consecutive_failures>=DISABLE_AFTER and ep.active: ep.active=False;log.warning('webhook endpoint %s disabled after %s consecutive failures',ep.id,ep.consecutive_failures)
 s.commit();return d.status
def dispatch_webhooks(s,limit=20,post=None):
 """ارسال سررسیدها؛ هر ردیف با UPDATE شرطی «claim» می‌شود تا چند worker دوبار نفرستند."""
 now=utcnow()
 s.execute(update(WebhookDelivery).where(WebhookDelivery.status=='sending',WebhookDelivery.next_try_at<now-STALE_SENDING).values(status='pending'));s.commit()
 res={'delivered':0,'retry':0,'failed':0}
 for did in s.scalars(select(WebhookDelivery.id).where(WebhookDelivery.status=='pending',WebhookDelivery.next_try_at<=now).order_by(WebhookDelivery.id).limit(limit)).all():
  if not s.execute(update(WebhookDelivery).where(WebhookDelivery.id==did,WebhookDelivery.status=='pending').values(status='sending',next_try_at=utcnow())).rowcount: s.commit();continue
  s.commit();d=s.get(WebhookDelivery,did);ep=s.get(WebhookEndpoint,d.endpoint_id)
  if not ep or not ep.active: d.status='failed';d.error='اندپوینت غیرفعال یا حذف شده است';s.commit();res['failed']+=1;continue
  st=deliver_one(s,d,ep,post);res['delivered' if st=='delivered' else 'failed' if st=='failed' else 'retry']+=1
 return res
def purge_deliveries(s,days=30):
 from sqlalchemy import delete
 n=s.execute(delete(WebhookDelivery).where(WebhookDelivery.status.in_(('delivered','failed')),WebhookDelivery.created_at<utcnow()-timedelta(days=days))).rowcount;s.commit();return n
