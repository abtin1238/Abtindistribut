from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .service import sync as _s_sync, my_events as _s_my_events

router=APIRouter()

@router.post('/api/sync')
def sync(payload: dict, ctx=Depends(current), s: Session=Depends(db)):
 return _s_sync(payload=payload, ctx=ctx, s=s)

@router.get('/api/sync/events')
def my_events(status: str | None=None, limit: int=100, ctx=Depends(current), s: Session=Depends(db)):
 'تاریخچه\u200cی رویدادهای همگام\u200cشده\u200cی خودِ کاربر (برای نمایش ردشده/تعارض به کلاینت آفلاین)'
 return _s_my_events(status=status, limit=limit, ctx=ctx, s=s)
