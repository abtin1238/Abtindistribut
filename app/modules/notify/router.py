from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .schemas import PrefsIn, ContactIn, TestIn, PushIn, PushDel
from .service import events as _s_events, prefs_get as _s_prefs_get, prefs_put as _s_prefs_put, contact_put as _s_contact_put, feed as _s_feed, unread_count as _s_unread_count, read_all as _s_read_all, test_send as _s_test_send, vapid_key as _s_vapid_key, push_sub as _s_push_sub, push_unsub as _s_push_unsub, deliveries as _s_deliveries, dispatch_now as _s_dispatch_now

router=APIRouter()

@router.get('/api/notifications/events')
def events(ctx=Depends(current)):
 return _s_events(ctx=ctx)

@router.get('/api/notifications/preferences')
def prefs_get(ctx=Depends(current), s: Session=Depends(db)):
 return _s_prefs_get(ctx=ctx, s=s)

@router.put('/api/notifications/preferences')
def prefs_put(x: PrefsIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_prefs_put(x=x, ctx=ctx, s=s)

@router.put('/api/me/contact')
def contact_put(x: ContactIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_contact_put(x=x, ctx=ctx, s=s)

@router.get('/api/notifications/feed')
def feed(unread: bool=False, event: Optional[str]=None, before_id: Optional[int]=None, limit: int=Query(30, ge=1, le=100), ctx=Depends(current), s: Session=Depends(db)):
 return _s_feed(unread=unread, event=event, before_id=before_id, limit=limit, ctx=ctx, s=s)

@router.get('/api/notifications/unread-count')
def unread_count(ctx=Depends(current), s: Session=Depends(db)):
 return _s_unread_count(ctx=ctx, s=s)

@router.post('/api/notifications/read-all')
def read_all(ctx=Depends(current), s: Session=Depends(db)):
 return _s_read_all(ctx=ctx, s=s)

@router.post('/api/notifications/test')
def test_send(x: TestIn, ctx=Depends(current), s: Session=Depends(db)):
 'ارسال آزمایشی به خودِ کاربر با کانال انتخابی (حداکثر ۵ بار در ساعت برای جلوگیری از سوءاستفاده/هزینه\u200cی پیامک)'
 return _s_test_send(x=x, ctx=ctx, s=s)

@router.get('/api/push/vapid-public-key')
def vapid_key(ctx=Depends(current)):
 return _s_vapid_key(ctx=ctx)

@router.post('/api/push/subscribe')
def push_sub(x: PushIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_push_sub(x=x, ctx=ctx, s=s)

@router.post('/api/push/unsubscribe')
def push_unsub(x: PushDel, ctx=Depends(current), s: Session=Depends(db)):
 return _s_push_unsub(x=x, ctx=ctx, s=s)

@router.get('/api/notifications/deliveries')
def deliveries(ctx=Depends(current), s: Session=Depends(db)):
 'وضعیت صف ارسال (فقط مدیر)'
 return _s_deliveries(ctx=ctx, s=s)

@router.post('/api/notifications/dispatch')
def dispatch_now(ctx=Depends(current), s: Session=Depends(db)):
 'اجرای فوری هشدارهای دوره\u200cای (کمبود موجودی، سررسید چک) و ارسال صف؛ فقط مدیر'
 return _s_dispatch_now(ctx=ctx, s=s)
