"""تبدیل واحد: همهٔ موجودی/قیمت/بهای تمام‌شده به «واحد پایه»ی کالا نگه‌داری می‌شود؛ ورودی‌های سفارش/خرید/انتقال می‌توانند واحد فرعی (کارتن/پالت) بدهند."""
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D
from app.models import Product, UnitConversion

C4 = Decimal('0.0001')


def factor_of(s: Session, cid: int, product_id: int, unit: str) -> Decimal:
    """ضریب واحد نسبت به واحد پایه؛ واحد خالی یا برابر واحد پایه = ۱."""
    unit = (unit or '').strip()
    if not unit:
        return Decimal(1)
    p = s.get(Product, product_id)
    if not p or p.company_id != cid:
        raise HTTPException(404, 'کالا یافت نشد')
    if unit == p.unit:
        return Decimal(1)
    uc = s.scalar(select(UnitConversion).where(UnitConversion.product_id == product_id, UnitConversion.unit == unit))
    if not uc:
        raise HTTPException(400, f'واحد «{unit}» برای کالای «{p.name}» تعریف نشده است')
    return D(uc.factor)


def to_base_qty(s: Session, cid: int, product_id: int, unit: str, qty) -> Decimal:
    return D(qty) * factor_of(s, cid, product_id, unit)


def to_base_cost(s: Session, cid: int, product_id: int, unit: str, unit_cost) -> Decimal:
    """بهای هر واحد فرعی → بهای هر واحد پایه"""
    return (D(unit_cost) / factor_of(s, cid, product_id, unit)).quantize(C4)
