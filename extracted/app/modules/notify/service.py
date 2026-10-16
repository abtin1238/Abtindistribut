from __future__ import annotations
import hashlib
import os
import re
from datetime import timedelta
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.core.common import audit, obj
from app.core.config import utcnow
from app.core.security import has_all, has_perm
from app.models import Notification, NotificationDelivery, NotificationPreference, PushSubscription, User
from app.services.notify import CHANNEL_LABELS, CHANNELS, EVENTS, EXTERNAL, dispatch_pending, prefs_for, push_endpoint_ok, run_alerts, SMS_GATEWAYS
from .schemas import PrefsIn, ContactIn, TestIn, PushIn, PushDel

EMAIL_RE=re.compile(r'^[^@\s]{1,100}@[^@\s]{1,100}\.[^@\s]{2,20}$');PHONE_RE=re.compile(r'^\+?\d{8,15}$')



def available():
 try: import pywebpush  # noqa: F401
 except ImportError: wp=False
 else: wp=True
 return {'inapp':True,'email':bool(os.getenv('SMTP_HOST')),'sms':os.getenv('SMS_PROVIDER','') in SMS_GATEWAYS,'webpush':wp and bool(os.getenv('VAPID_PRIVATE_KEY'))}

def events(ctx):
 av=available();return {'events':[{'code':c,'title':t,'default_channels':sorted(d)} for c,(t,d) in EVENTS.items()],'channels':[{'code':c,'label':CHANNEL_LABELS[c],'available':av[c]} for c in CHANNELS]}

def prefs_get(ctx, s: Session):
 u,cid,r=ctx;eff=prefs_for(s,cid,u.id)
 return {'prefs':{e:{c:(c in eff[e]) for c in CHANNELS} for e in EVENTS},'contact':{'email':u.email or '','phone':u.phone or ''},'push_subscriptions':s.scalar(select(func.count()).select_from(PushSubscription).where(PushSubscription.user_id==u.id)) or 0}

def prefs_put(x: PrefsIn, ctx, s: Session):
 u,cid,r=ctx
 for e,m in x.prefs.items():
  if e not in EVENTS: raise HTTPException(400,'رویداد نامعتبر: '+e)
  for c,v in m.items():
   if c not in CHANNELS: raise HTTPException(400,'کانال نامعتبر: '+c)
   row=s.scalar(select(NotificationPreference).where(NotificationPreference.company_id==cid,NotificationPreference.user_id==u.id,NotificationPreference.event==e,NotificationPreference.channel==c))
   if row: row.enabled=v
   else: s.add(NotificationPreference(company_id=cid,user_id=u.id,event=e,channel=c,enabled=v))
 audit(s,cid,u.id,'update','notification_prefs');s.commit();return prefs_get(ctx,s)

def contact_put(x: ContactIn, ctx, s: Session):
 u,cid,r=ctx;em=x.email.strip();ph=re.sub(r'[\s\-()]','',x.phone.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹','0123456789')))
 if em and not EMAIL_RE.match(em): raise HTTPException(400,'ایمیل نامعتبر است')
 if ph and not PHONE_RE.match(ph): raise HTTPException(400,'شماره موبایل نامعتبر است')
 q=s.get(User,u.id);q.email=em;q.phone=ph;audit(s,cid,u.id,'update','user_contact',u.id);s.commit();return {'email':q.email,'phone':q.phone}

def feed(unread: bool, event: Optional[str], before_id: Optional[int], limit: int, ctx, s: Session):
 u,cid,r=ctx;q=select(Notification).where(Notification.company_id==cid,Notification.user_id==u.id)
 if unread: q=q.where(Notification.read==False)
 if event: q=q.where(Notification.event==event)
 if before_id: q=q.where(Notification.id<before_id)
 rows=[{k:v for k,v in obj(x).items() if k!='dedupe_key'} for x in s.scalars(q.order_by(Notification.id.desc()).limit(limit))]
 return {'items':rows,'unread':s.scalar(select(func.count()).select_from(Notification).where(Notification.company_id==cid,Notification.user_id==u.id,Notification.read==False)) or 0}

def unread_count(ctx, s: Session):
 return {'unread':s.scalar(select(func.count()).select_from(Notification).where(Notification.company_id==ctx[1],Notification.user_id==ctx[0].id,Notification.read==False)) or 0}

def read_all(ctx, s: Session):
 n=s.execute(update(Notification).where(Notification.company_id==ctx[1],Notification.user_id==ctx[0].id,Notification.read==False).values(read=True)).rowcount;s.commit();return {'marked':n}

def test_send(x: TestIn, ctx, s: Session):
 """ارسال آزمایشی به خودِ کاربر با کانال انتخابی (حداکثر ۵ بار در ساعت برای جلوگیری از سوءاستفاده/هزینه‌ی پیامک)"""
 u,cid,r=ctx
 if x.channel not in EXTERNAL: raise HTTPException(400,'کانال آزمایشی باید email/sms/webpush باشد')
 q=s.get(User,u.id)
 if x.channel=='email' and not q.email: raise HTTPException(400,'ابتدا ایمیل خود را ثبت کنید')
 if x.channel=='sms' and not q.phone: raise HTTPException(400,'ابتدا شماره موبایل خود را ثبت کنید')
 if x.channel=='webpush' and not s.scalar(select(PushSubscription.id).where(PushSubscription.user_id==u.id).limit(1)): raise HTTPException(400,'مرورگری برای اعلان ثبت نشده است')
 if (s.scalar(select(func.count()).select_from(NotificationDelivery).where(NotificationDelivery.user_id==u.id,NotificationDelivery.created_at>=utcnow()-timedelta(hours=1),NotificationDelivery.notification_id.in_(select(Notification.id).where(Notification.user_id==u.id,Notification.event=='system')))) or 0)>=5: raise HTTPException(429,'تعداد ارسال آزمایشی در ساعت گذشته به سقف رسیده است')
 n=Notification(company_id=cid,user_id=u.id,title='اعلان آزمایشی',body='این پیام آزمایشی از Abtin Distribution است.',read=True,event='system');s.add(n);s.flush()
 d=NotificationDelivery(company_id=cid,notification_id=n.id,user_id=u.id,channel=x.channel);s.add(d);s.commit();dispatch_pending(s,limit=5);s.refresh(d)
 return {'status':d.status,'error':d.error}

def vapid_key(ctx):
 k=os.getenv('VAPID_PUBLIC_KEY','')
 if not k: raise HTTPException(404,'Web Push تنظیم نشده است')
 return {'key':k}

def push_sub(x: PushIn, ctx, s: Session):
 u,cid,r=ctx
 if not push_endpoint_ok(x.endpoint): raise HTTPException(400,'نشانی سرویس اعلان مرورگر مجاز نیست')
 h=hashlib.sha256(x.endpoint.encode()).hexdigest();row=s.scalar(select(PushSubscription).where(PushSubscription.user_id==u.id,PushSubscription.endpoint_hash==h))
 if row: row.p256dh=x.keys.p256dh;row.auth=x.keys.auth;row.company_id=cid
 else: s.add(PushSubscription(company_id=cid,user_id=u.id,endpoint=x.endpoint,endpoint_hash=h,p256dh=x.keys.p256dh,auth=x.keys.auth))
 s.commit();return {'ok':True}

def push_unsub(x: PushDel, ctx, s: Session):
 h=hashlib.sha256(x.endpoint.encode()).hexdigest();row=s.scalar(select(PushSubscription).where(PushSubscription.user_id==ctx[0].id,PushSubscription.endpoint_hash==h))
 if row: s.delete(row);s.commit()
 return {'ok':True}

def deliveries(ctx, s: Session):
 """وضعیت صف ارسال (فقط مدیر)"""
 if not has_all(ctx[2]) and not has_perm(ctx[2],'admin.read'): raise HTTPException(403,'دسترسی کافی نیست')
 cid=ctx[1];cnt={f'{c}:{st}':n for c,st,n in s.execute(select(NotificationDelivery.channel,NotificationDelivery.status,func.count()).where(NotificationDelivery.company_id==cid).group_by(NotificationDelivery.channel,NotificationDelivery.status))}
 bad=[obj(d) for d in s.scalars(select(NotificationDelivery).where(NotificationDelivery.company_id==cid,NotificationDelivery.status.in_(['failed','skipped'])).order_by(NotificationDelivery.id.desc()).limit(20))]
 return {'counts':cnt,'recent_problems':bad,'available':available()}

def dispatch_now(ctx, s: Session):
 """اجرای فوری هشدارهای دوره‌ای (کمبود موجودی، سررسید چک) و ارسال صف؛ فقط مدیر"""
 if not has_all(ctx[2]): raise HTTPException(403,'دسترسی کافی نیست')
 return {'alerts':run_alerts(s),'dispatch':dispatch_pending(s)}
