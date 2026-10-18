from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.schemas import CostAllocationIn, PurchaseIn, PurchaseReceiptIn, PurchaseReturnIn
from .service import suppliers as _s_suppliers, add_supplier as _s_add_supplier, purchases as _s_purchases, purchase_detail as _s_purchase_detail, create_purchase as _s_create_purchase, receive_purchase as _s_receive_purchase, return_purchase as _s_return_purchase, cancel_purchase as _s_cancel_purchase, allocate_cost as _s_allocate_cost

router=APIRouter()

@router.get('/api/suppliers')
def suppliers(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_suppliers(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.post('/api/suppliers')
def add_supplier(payload: dict, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_supplier(payload=payload, ctx=ctx, s=s)

@router.get('/api/purchases')
def purchases(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_purchases(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.get('/api/purchases/{pid}')
def purchase_detail(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_purchase_detail(pid=pid, ctx=ctx, s=s)

@router.post('/api/purchases')
def create_purchase(x: PurchaseIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_purchase(x=x, ctx=ctx, s=s)

@router.post('/api/purchases/{pid}/receive')
def receive_purchase(pid: int, x: Optional[PurchaseReceiptIn]=None, ctx=Depends(current), s: Session=Depends(db)):
 'رسید کامل (بدون بدنه) یا جزئی (items) — باقیمانده در وضعیت partial می‌ماند'
 return _s_receive_purchase(pid=pid, ctx=ctx, s=s, x=x)

@router.post('/api/purchases/{pid}/cancel')
def cancel_purchase(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 'لغو سفارش خرید پیش‌نویس بدون رسید'
 return _s_cancel_purchase(pid=pid, ctx=ctx, s=s)

@router.post('/api/purchases/{pid}/allocate-cost')
def allocate_cost(pid: int, x: CostAllocationIn, ctx=Depends(current), s: Session=Depends(db)):
 'تسهیم هزینهٔ جانبی (گمرک/حمل/بیمه) روی اقلام پیش از رسید'
 return _s_allocate_cost(pid=pid, x=x, ctx=ctx, s=s)

@router.post('/api/purchases/{pid}/return')
def return_purchase(pid: int, x: PurchaseReturnIn, ctx=Depends(current), s: Session=Depends(db)):
 'برگشت از خرید: کاهش موجودی انبار، کاهش بدهی تأمین\u200cکننده با همان بهای رسید و بازمحاسبهٔ میانگین بهای کالا'
 return _s_return_purchase(pid=pid, x=x, ctx=ctx, s=s)
