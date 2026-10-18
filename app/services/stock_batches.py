"""بچ/لات و تاریخ انقضا. جمع بچ‌ها هرگز از موجودی ردیف Stock بیشتر نیست؛ مازاد = «بدون بچ» (موجودی قبل از فعال‌سازی)."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.common import D
from app.models import StockBatch


def add_batch(s: Session, cid: int, wid: int, pid: int, qty, batch_no: str, expiry: date | None):
    batch_no = (batch_no or '').strip()
    if not batch_no: raise HTTPException(400, 'شماره بچ الزامی است')
    b = s.scalar(select(StockBatch).where(StockBatch.warehouse_id == wid, StockBatch.product_id == pid, StockBatch.batch_no == batch_no).with_for_update())
    if b:
        if expiry and b.expiry_date and expiry != b.expiry_date: raise HTTPException(409, f'بچ {batch_no} با تاریخ انقضای دیگری ثبت شده است')
        b.quantity = D(b.quantity) + D(qty)
        if expiry and not b.expiry_date: b.expiry_date = expiry
        return b
    b = StockBatch(company_id=cid, warehouse_id=wid, product_id=pid, batch_no=batch_no, expiry_date=expiry, quantity=D(qty)); s.add(b); return b


def batched_qty(s: Session, wid: int, pid: int) -> Decimal:
    return D(s.scalar(select(func.coalesce(func.sum(StockBatch.quantity), 0)).where(StockBatch.warehouse_id == wid, StockBatch.product_id == pid)))


def consume_batches(s: Session, cid: int, wid: int, pid: int, qty, batch_no: str = '', strict: bool = False, out: list | None = None) -> Decimal:
    """FEFO (زودترین انقضا اول؛ بدون انقضا آخر). strict=True: اگر نشد خطا؛ strict=False: هر چه بچ هست برمی‌دارد (برای تحویل/برگشت که نباید شکست بخورد).
    مقدار «بدون بچ» را برمی‌گرداند."""
    q = select(StockBatch).where(StockBatch.warehouse_id == wid, StockBatch.product_id == pid, StockBatch.quantity > 0).order_by(StockBatch.expiry_date.is_(None), StockBatch.expiry_date, StockBatch.id).with_for_update()
    if batch_no: q = q.where(StockBatch.batch_no == batch_no.strip())
    left = D(qty)
    for b in s.scalars(q).all():
        take = min(D(b.quantity), left); b.quantity = D(b.quantity) - take; left -= take
        if out is not None: out.append((b.batch_no, b.expiry_date, take))
        if left <= 0: break
    if left > 0 and batch_no and strict: raise HTTPException(400, 'موجودی بچ انتخاب‌شده کافی نیست')
    return left
