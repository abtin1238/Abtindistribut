"""منطق خالص بهای تمام‌شده (بدون وابستگی به FastAPI/SQLAlchemy تا مستقیم قابل‌تست باشد).

قرارداد: میانگین موزون متحرک در سطح «شرکت × کالا» (نه انبار)؛ انتقال بین انبارها بها را عوض نمی‌کند.
"""
from __future__ import annotations
from decimal import Decimal

Q2 = Decimal('0.01')
C4 = Decimal('0.0001')


def _d(v):
    return Decimal(str(v if v is not None else 0))


def weighted_avg(on_hand, avg_cost, qty_in, unit_cost):
    """بهای میانگین جدید پس از ورود qty_in با بهای unit_cost. موجودی منفی/صفر وزن ندارد."""
    have = max(_d(on_hand), Decimal(0))
    q = _d(qty_in)
    if q <= 0:
        raise ValueError('مقدار ورود باید مثبت باشد')
    tot = have + q
    return ((have * _d(avg_cost) + q * _d(unit_cost)) / tot).quantize(C4)


def weighted_avg_out(on_hand, avg_cost, qty_out, unit_cost):
    """بهای میانگین جدید پس از «برگشت از خرید» qty_out با بهای واحد رسید unit_cost.

    ارزش موجودی (on_hand×avg) به‌اندازهٔ همان مبلغی که سند برگشت از حساب موجودی کم می‌کند (qty_out×unit_cost)
    کم می‌شود و بر موجودی باقی‌مانده تقسیم می‌گردد؛ پس ارزش کالا در انبار با دفتر کل هم‌خوان می‌ماند.
    اگر چیزی باقی نماند یا نتیجه منفی شود (داده‌ی ناسازگار) میانگین قبلی دست‌نخورده می‌ماند."""
    have = _d(on_hand)
    q = _d(qty_out)
    if q <= 0:
        raise ValueError('مقدار خروج باید مثبت باشد')
    left = have - q
    if left <= 0:
        return _d(avg_cost).quantize(C4)
    new = (have * _d(avg_cost) - q * _d(unit_cost)) / left
    if new < 0:
        return _d(avg_cost).quantize(C4)
    return new.quantize(C4)


def allocate_freight(nets, qtys, freight):
    """هزینه‌ی جانبی (حمل/گمرک) را به نسبت ارزش خالص (در نبود ارزش: به نسبت تعداد) تسهیم می‌کند؛
    مجموع سهم‌ها دقیقاً برابر freight است (باقی‌مانده‌ی گرد‌کردن به آخرین سطر می‌رود)."""
    f = _d(freight)
    if f < 0:
        raise ValueError('هزینه‌ی جانبی منفی است')
    if not nets:
        return []
    base = [_d(n) for n in nets]
    tot = sum(base, Decimal(0))
    if tot <= 0:
        base = [_d(q) for q in qtys]
        tot = sum(base, Decimal(0))
    if tot <= 0 or f == 0:
        return [Decimal(0)] * len(nets)
    out = [(f * b / tot).quantize(Q2) for b in base]
    out[-1] += f - sum(out, Decimal(0))
    return out


def line_unit_cost(qty, gross, discount, landed):
    """بهای واحد خالص یک سطر خرید: (مبلغ − تخفیف + سهم هزینه‌ی جانبی) / تعداد."""
    q = _d(qty)
    if q <= 0:
        raise ValueError('تعداد باید مثبت باشد')
    return ((_d(gross) - _d(discount) + _d(landed)) / q).quantize(C4)


def split_return_discount(unit_price, qty, net_amount):
    """سهم تخفیف از یک برگشتی: (قیمت×تعداد) − مبلغ خالص؛ هرگز منفی نمی‌شود."""
    return max(Decimal(0), (_d(unit_price) * _d(qty)).quantize(Q2) - _d(net_amount))
