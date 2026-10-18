"""سیستم اعلان: رویدادها، ترجیح هر کاربر، کانال‌های قابل‌تعویض (درون‌برنامه، ایمیل، پیامک، Web Push) و صف ارسال.

- `notify()` اعلان درون‌برنامه می‌سازد و برای کانال‌های بیرونیِ فعال، ردیف `NotificationDelivery` می‌گذارد (commit با فراخوان).
- `dispatch_pending()` صف را ارسال می‌کند (در حلقه‌ی پس‌زمینه‌ی main)؛ خطا → تلاش مجدد تا MAX_ATTEMPTS، سپس failed.
- کانال بدون تنظیم محیطی → وضعیت `skipped` (بدون تلاش مجدد). هیچ کلید/رمزی در کد نیست؛ همه از env:
  SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS، SMS_PROVIDER=log|webhook + SMS_WEBHOOK_URL/TOKEN، VAPID_PRIVATE_KEY/VAPID_PUBLIC_KEY/VAPID_SUBJECT.
- درگاه پیامک قابل‌تعویض است: `register_sms_gateway('name', fn(phone, text))`.
"""
from __future__ import annotations
import json
import logging
import os
import smtplib
import urllib.request
from datetime import date,timedelta
from email.message import EmailMessage
from urllib.parse import urlparse
from sqlalchemy import func,select
from app.core.config import utcnow
from app.core.security import has_perm
from app.models import Check,Company,Membership,Notification,NotificationDelivery,NotificationPreference,Product,PushSubscription,Role,Stock,User
from app.services import webhooks as wh
from app.services.jalali import fmt_jalali

log=logging.getLogger('abtin')
CHANNELS=('inapp','email','sms','webpush');EXTERNAL=('email','sms','webpush')
CHANNEL_LABELS={'inapp':'درون‌برنامه','email':'ایمیل','sms':'پیامک','webpush':'اعلان مرورگر'}
MAX_ATTEMPTS=5
# رویداد: (عنوان، کانال‌های پیش‌فرض). کانال‌های بیرونی به‌صورت پیش‌فرض خاموش‌اند (هزینه/حریم خصوصی) و کاربر روشنشان می‌کند.
EVENTS={'order_new':('سفارش جدید',{'inapp'}),'invoice_approved':('تأیید فاکتور',{'inapp'}),'delivery_new':('ماموریت جدید',{'inapp'}),'delivery_done':('تحویل موفق',{'inapp'}),'delivery_failed':('عدم تحویل',{'inapp'}),'low_stock':('کمبود موجودی',{'inapp'}),'check_due':('سررسید چک',{'inapp'}),'task_assigned':('وظیفه‌ی جدید',{'inapp'}),'task_reminder':('یادآوری وظیفه/تماس',{'inapp'}),'lead_followup':('پیگیری سرنخ',{'inapp'}),'system':('اعلان سیستمی',{'inapp'})}
# مجوز لازم برای دیدن/تنظیم هر رویداد (None = برای همه). کاربر فقط رویدادهای مرتبط با نقش خودش را می‌بیند.
EVENT_PERM={'order_new':'sales.approve','invoice_approved':'sales.write','delivery_new':'delivery.read','delivery_done':'sales.write','delivery_failed':'sales.write','low_stock':'inventory.write','check_due':'finance.write','task_assigned':'automation.write','task_reminder':'automation.write','lead_followup':'automation.write','system':None}
def events_for_role(r):
 """رویدادهای مجاز برای نقش (مدیر کل همه را می‌بیند)"""
 return {e for e in EVENTS if not EVENT_PERM.get(e) or has_perm(r,EVENT_PERM[e])}
class NotConfigured(Exception): pass

def prefs_for(s,cid,uid):
 """نقشه‌ی {event: set(channels)} مؤثر برای یک کاربر (پیش‌فرض + بازنویسی کاربر)"""
 eff={e:set(d) for e,(_,d) in EVENTS.items()}
 for p in s.scalars(select(NotificationPreference).where(NotificationPreference.company_id==cid,NotificationPreference.user_id==uid)):
  if p.event in eff and p.channel in CHANNELS: (eff[p.event].add if p.enabled else eff[p.event].discard)(p.channel)
 return eff
def users_with_perm(s,cid,perm):
 """شناسه‌ی کاربران فعالِ عضو شرکت که نقششان مجوز دارد"""
 q=select(User,Role).join(Role,Role.id==User.role_id).join(Membership,Membership.user_id==User.id).where(Membership.company_id==cid,User.active==True)
 return sorted({u.id for u,r in s.execute(q) if has_perm(r,perm)})
def notify(s,cid,user_ids,event,title,body='',entity='',entity_id=None,dedupe=None):
 """اعلان برای کاربران؛ بدون commit. با `dedupe` از تکرار جلوگیری می‌شود. تعداد کاربران اعلان‌گرفته را برمی‌گرداند."""
 if event not in EVENTS: raise ValueError('رویداد ناشناخته: '+event)
 n=0
 try:
  with s.begin_nested(): wh.emit_from_notify(s,cid,event,title,body,entity,entity_id,dedupe)   # وبهوک خروجی؛ خطایش اعلان را خراب نمی‌کند
 except Exception: log.exception('webhook emit failed')
 for uid in dict.fromkeys(user_ids or []):
  if dedupe and s.scalar(select(Notification.id).where(Notification.company_id==cid,Notification.user_id==uid,Notification.dedupe_key==dedupe)): continue
  ch=prefs_for(s,cid,uid)[event]
  if not ch: continue
  u=s.get(User,uid)
  if not u or not u.active: continue
  nobj=Notification(company_id=cid,user_id=uid,title=title[:200],body=body,read=('inapp' not in ch),event=event,entity=entity,entity_id=entity_id,dedupe_key=dedupe);s.add(nobj);s.flush();nid=nobj.id
  for c in EXTERNAL:
   if c not in ch: continue
   if c=='email' and not u.email: continue
   if c=='sms' and not u.phone: continue
   if c=='webpush' and not s.scalar(select(PushSubscription.id).where(PushSubscription.user_id==uid).limit(1)): continue
   s.add(NotificationDelivery(company_id=cid,notification_id=nid,user_id=uid,channel=c))
  n+=1
 return n

# ---------------------------------------------------------------- کانال‌ها
def _clean(t,n): return ' '.join(str(t).split())[:n]
def send_email(u,title,body):
 host=os.getenv('SMTP_HOST','')
 if not host: raise NotConfigured('SMTP_HOST تنظیم نشده است')
 m=EmailMessage();m['Subject']=_clean(title,150);m['From']=os.getenv('SMTP_FROM',os.getenv('SMTP_USER','noreply@localhost'));m['To']=_clean(u.email,200);m.set_content(body or title)
 port=int(os.getenv('SMTP_PORT','587'));tls=os.getenv('SMTP_TLS','starttls')
 cls=smtplib.SMTP_SSL if tls=='ssl' else smtplib.SMTP
 with cls(host,port,timeout=15) as c:
  if tls=='starttls': c.starttls()
  if os.getenv('SMTP_USER'): c.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD',''))
  c.send_message(m)
def _sms_log(phone,text): log.info('SMS(log) to=%s text=%s',phone[-4:].rjust(len(phone),'*'),text)
def _sms_webhook(phone,text):
 url=os.getenv('SMS_WEBHOOK_URL','')
 if not url.startswith(('https://','http://')): raise NotConfigured('SMS_WEBHOOK_URL تنظیم نشده است')
 req=urllib.request.Request(url,data=json.dumps({'to':phone,'message':text}).encode(),headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+os.getenv('SMS_WEBHOOK_TOKEN')} if os.getenv('SMS_WEBHOOK_TOKEN') else {})},method='POST')
 with urllib.request.urlopen(req,timeout=10) as r:
  if r.status>=300: raise RuntimeError(f'درگاه پیامک کد {r.status} داد')
SMS_GATEWAYS={'log':_sms_log,'webhook':_sms_webhook}
def register_sms_gateway(name,fn): SMS_GATEWAYS[name]=fn
def send_sms(u,title,body):
 name=os.getenv('SMS_PROVIDER','')
 if name not in SMS_GATEWAYS: raise NotConfigured('SMS_PROVIDER تنظیم نشده یا ناشناخته است')
 SMS_GATEWAYS[name](u.phone,_clean(title+(': '+body if body else ''),300))
PUSH_HOSTS=('fcm.googleapis.com','updates.push.services.mozilla.com','push.services.mozilla.com','web.push.apple.com','notify.windows.com','push.apple.com')
def push_endpoint_ok(endpoint):
 """جلوگیری از SSRF: فقط HTTPS و سرویس‌های Push شناخته‌شده"""
 p=urlparse(endpoint or '');h=(p.hostname or '').lower()
 return p.scheme=='https' and any(h==x or h.endswith('.'+x) for x in PUSH_HOSTS)
def send_webpush(s,u,n):
 key=os.getenv('VAPID_PRIVATE_KEY','')
 if not key: raise NotConfigured('VAPID_PRIVATE_KEY تنظیم نشده است')
 try: from pywebpush import WebPushException,webpush
 except ImportError: raise NotConfigured('بسته‌ی pywebpush نصب نیست')
 sent=0;last=None
 for sub in s.scalars(select(PushSubscription).where(PushSubscription.user_id==u.id)):
  if not push_endpoint_ok(sub.endpoint): continue
  try:
   webpush({'endpoint':sub.endpoint,'keys':{'p256dh':sub.p256dh,'auth':sub.auth}},json.dumps({'title':n.title,'body':n.body,'url':'/'}),vapid_private_key=key,vapid_claims={'sub':os.getenv('VAPID_SUBJECT','mailto:admin@localhost')},timeout=10);sent+=1
  except WebPushException as e:
   last=e
   if getattr(e,'response',None) is not None and e.response.status_code in (404,410): s.delete(sub)   # اشتراک منقضی
 if not sent and last: raise last
def dispatch_pending(s,limit=50):
 """ارسال ردیف‌های pending؛ نتیجه {'sent','failed','skipped'}"""
 res={'sent':0,'failed':0,'skipped':0}
 for d in s.scalars(select(NotificationDelivery).where(NotificationDelivery.status=='pending').order_by(NotificationDelivery.id).limit(limit)).all():
  n=s.get(Notification,d.notification_id);u=s.get(User,d.user_id)
  try:
   if not n or not u or not u.active: raise NotConfigured('گیرنده یا اعلان معتبر نیست')
   if d.channel=='email': send_email(u,n.title,n.body)
   elif d.channel=='sms': send_sms(u,n.title,n.body)
   elif d.channel=='webpush': send_webpush(s,u,n)
   else: raise NotConfigured('کانال ناشناخته')
   d.status='sent';d.sent_at=utcnow();d.error='';res['sent']+=1
  except NotConfigured as e: d.status='skipped';d.error=str(e)[:300];res['skipped']+=1
  except Exception as e:
   d.attempts+=1;d.error=(str(e) or e.__class__.__name__)[:300]
   if d.attempts>=MAX_ATTEMPTS: d.status='failed';res['failed']+=1
   log.warning('notification delivery %s via %s failed (%s/%s): %s',d.id,d.channel,d.attempts,MAX_ATTEMPTS,d.error)
  s.commit()
 return res

# ---------------------------------------------------------------- هشدارهای دوره‌ای (idempotent با dedupe)
def run_alerts(s,today=None):
 """کمبود موجودی (هفته‌ای یک‌بار برای هر کالا) و سررسید چک (۷/۳/۱ روز مانده و سررسیدگذشته، هر مرحله یک‌بار). تعداد اعلان‌ها را برمی‌گرداند."""
 today=today or date.today();n=0;wk=today.isocalendar()
 for cid in s.scalars(select(Company.id).where(Company.active==True)):
  rcp=users_with_perm(s,cid,'inventory.write')
  if rcp:
   q=select(Product.id,Product.name,Product.min_stock,func.sum(Stock.quantity-Stock.reserved)).join(Stock,Stock.product_id==Product.id).where(Product.company_id==cid,Product.active==True,Product.min_stock>0).group_by(Product.id,Product.name,Product.min_stock)
   for pid,name,mn,avail in s.execute(q):
    if avail is not None and avail<=mn: n+=notify(s,cid,rcp,'low_stock','کمبود موجودی: '+name,f'موجودی قابل فروش {avail:g} از حداقل {mn:g} کمتر یا برابر است',entity='product',entity_id=pid,dedupe=f'low:{pid}:{wk[0]}-{wk[1]}')
  rcp=users_with_perm(s,cid,'finance.write')
  if rcp:
   for c in s.scalars(select(Check).where(Check.company_id==cid,Check.status.in_(['pending','deposited']),Check.due_date<=today+timedelta(days=7))):
    dl=(c.due_date-today).days;ms=0 if dl<0 else 1 if dl<=1 else 3 if dl<=3 else 7
    when='سررسید گذشته' if dl<0 else 'امروز' if dl==0 else f'{dl} روز دیگر'
    n+=notify(s,cid,rcp,'check_due',f'سررسید چک {c.number}',f'چک {"دریافتی" if c.kind=="received" else "پرداختی"} {c.number} به مبلغ {c.amount:,.0f} — سررسید {fmt_jalali(c.due_date)} ({when})',entity='check',entity_id=c.id,dedupe=f'chk:{c.id}:{ms}')
 s.commit();return n
