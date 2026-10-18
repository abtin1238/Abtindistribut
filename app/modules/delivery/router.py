from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import BulkAssignIn, CollectIn, DeliveryIn, DeliveryUpdate
from .service import assign_delivery as _s_assign_delivery, bulk_assign as _s_bulk_assign, board as _s_board, deliveries as _s_deliveries, my_deliveries as _s_my_deliveries, delivery_detail as _s_delivery_detail, delivery_photo as _s_delivery_photo, collect as _s_collect, update_delivery as _s_update_delivery, report_delivery as _s_report_delivery

router=APIRouter()

@router.post('/api/orders/{oid}/assign-delivery')
def assign_delivery(oid: int, x: DeliveryIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_assign_delivery(oid=oid, x=x, ctx=ctx, s=s)

@router.post('/api/deliveries/bulk-assign')
def bulk_assign(x: BulkAssignIn, ctx=Depends(current), s: Session=Depends(db)):
 'تخصیص چند سفارش به یک مأمور؛ هر سفارش مستقل است و نتیجه\u200cی تک\u200cتک برگردانده می\u200cشود.'
 return _s_bulk_assign(x=x, ctx=ctx, s=s)

@router.get('/api/deliveries/board')
def board(status: Optional[str]=None, day: Optional[date]=None, driver_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 'نمای مدیر: ماموریت\u200cها با نام مشتری/مأمور؛ سفارش\u200cهای تأییدشده\u200cی بدون ماموریت در `unassigned`.'
 return _s_board(status=status, day=day, driver_id=driver_id, ctx=ctx, s=s)

@router.get('/api/deliveries')
def deliveries(ctx=Depends(current), s: Session=Depends(db)):
 return _s_deliveries(ctx=ctx, s=s)

@router.get('/api/deliveries/mine')
def my_deliveries(day: Optional[date]=None, lat: Optional[float]=Query(None, ge=-90, le=90), lng: Optional[float]=Query(None, ge=-180, le=180), ctx=Depends(current), s: Session=Depends(db)):
 'ماموریت\u200cهای فعال + انجام\u200cشده\u200cی روز `day`؛ فعال\u200cها به ترتیب مسیر (نزدیک\u200cترین همسایه از نقطه\u200cی فعلی)'
 return _s_my_deliveries(day=day, lat=lat, lng=lng, ctx=ctx, s=s)

@router.get('/api/deliveries/{did}')
def delivery_detail(did: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_delivery_detail(did=did, ctx=ctx, s=s)

@router.post('/api/deliveries/{did}/photo')
async def delivery_photo(did: int, file: UploadFile=File(...), ctx=Depends(current), s: Session=Depends(db)):
 return await _s_delivery_photo(did=did, file=file, ctx=ctx, s=s)

@router.post('/api/deliveries/{did}/collect')
def collect(did: int, x: CollectIn, ctx=Depends(current), s: Session=Depends(db)):
 'وصول وجه/چک در محل؛ فقط روی ماموریت خود راننده. نقد/کارت/حواله به فاکتور تخصیص می\u200cیابد و سند می\u200cسازد؛ چک مثل ثبت چک عادی ثبت می\u200cشود (تخصیص به فاکتور ندارد).'
 return _s_collect(did=did, x=x, ctx=ctx, s=s)

@router.patch('/api/deliveries/{did}')
def update_delivery(did: int, x: DeliveryUpdate, ctx=Depends(current), s: Session=Depends(db)):
 return _s_update_delivery(did=did, x=x, ctx=ctx, s=s)

@router.get('/api/reports/delivery')
def report_delivery(start: Optional[date]=Query(None), end: Optional[date]=Query(None), driver_id: Optional[int]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_report_delivery(start=start, end=end, driver_id=driver_id, ctx=ctx, s=s)
