from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .service import summary as _s_summary, trend as _s_trend, holding as _s_holding, recon as _s_recon

router=APIRouter()

@router.get('/api/ceo/summary')
def summary(ctx=Depends(current), s: Session=Depends(db)):
 return _s_summary(ctx=ctx, s=s)

@router.get('/api/ceo/trend')
def trend(days: int=Query(30, ge=7, le=366), ctx=Depends(current), s: Session=Depends(db)):
 return _s_trend(days=days, ctx=ctx, s=s)

@router.get('/api/ceo/holding')
def holding(ctx=Depends(current), s: Session=Depends(db)):
 'مقایسه و تجمیع (Consolidation) شرکت\u200cهای هم\u200cگروه که کاربر عضو آن\u200cهاست'
 return _s_holding(ctx=ctx, s=s)

@router.get('/api/ceo/reconcile')
def recon(ctx=Depends(current), s: Session=Depends(db)):
 return _s_recon(ctx=ctx, s=s)
