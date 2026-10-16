from __future__ import annotations
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.schemas import BrandingIn, InvoiceTermsIn, TaxIn
from app.services.files import sniff_type  # noqa: F401
from .schemas import ThemeIn
from .service import notifications as _s_notifications, notification_read as _s_notification_read, dashboard as _s_dashboard, search as _s_search, dash_trend as _s_dash_trend, dash_cat as _s_dash_cat, theme_get as _s_theme_get, theme_put as _s_theme_put, brand_get as _s_brand_get, brand_put as _s_brand_put, logo_upload as _s_logo_upload, logo_delete as _s_logo_delete, logo_get as _s_logo_get, tax_get as _s_tax_get, tax_put as _s_tax_put, invoice_terms_get as _s_invoice_terms_get, invoice_terms_put as _s_invoice_terms_put

router=APIRouter()

@router.get('/api/notifications')
def notifications(ctx=Depends(current), s: Session=Depends(db)):
 return _s_notifications(ctx=ctx, s=s)

@router.post('/api/notifications/{nid}/read')
def notification_read(nid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_notification_read(nid=nid, ctx=ctx, s=s)

@router.get('/api/dashboard')
def dashboard(ctx=Depends(current), s: Session=Depends(db)):
 return _s_dashboard(ctx=ctx, s=s)

@router.get('/api/search')
def search(q: str=Query(..., min_length=1, max_length=100), ctx=Depends(current), s: Session=Depends(db)):
 return _s_search(q=q, ctx=ctx, s=s)

@router.get('/api/dashboard/trend')
def dash_trend(days: int=Query(30, ge=1, le=366), ctx=Depends(current), s: Session=Depends(db)):
 return _s_dash_trend(days=days, ctx=ctx, s=s)

@router.get('/api/dashboard/by-category')
def dash_cat(days: int=Query(30, ge=1, le=366), ctx=Depends(current), s: Session=Depends(db)):
 return _s_dash_cat(days=days, ctx=ctx, s=s)

@router.get('/api/settings/theme')
def theme_get(ctx=Depends(current), s: Session=Depends(db)):
 return _s_theme_get(ctx=ctx, s=s)

@router.put('/api/settings/theme')
def theme_put(x: ThemeIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_theme_put(x=x, ctx=ctx, s=s)

@router.get('/api/settings/brand')
def brand_get(ctx=Depends(current), s: Session=Depends(db)):
 return _s_brand_get(ctx=ctx, s=s)

@router.put('/api/settings/brand')
def brand_put(x: BrandingIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_brand_put(x=x, ctx=ctx, s=s)

@router.post('/api/settings/logo')
async def logo_upload(file: UploadFile=File(...), ctx=Depends(current), s: Session=Depends(db)):
 return await _s_logo_upload(file=file, ctx=ctx, s=s)

@router.delete('/api/settings/logo')
def logo_delete(ctx=Depends(current), s: Session=Depends(db)):
 return _s_logo_delete(ctx=ctx, s=s)

@router.get('/api/brand/logo/{cid}')
def logo_get(cid: int, s: Session=Depends(db)):
 return _s_logo_get(cid=cid, s=s)

@router.get('/api/settings/tax')
def tax_get(ctx=Depends(current), s: Session=Depends(db)):
 return _s_tax_get(ctx=ctx, s=s)

@router.put('/api/settings/tax')
def tax_put(x: TaxIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_tax_put(x=x, ctx=ctx, s=s)

@router.get('/api/settings/invoice-terms')
def invoice_terms_get(ctx=Depends(current), s: Session=Depends(db)):
 return _s_invoice_terms_get(ctx=ctx, s=s)

@router.put('/api/settings/invoice-terms')
def invoice_terms_put(x: InvoiceTermsIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_invoice_terms_put(x=x, ctx=ctx, s=s)
