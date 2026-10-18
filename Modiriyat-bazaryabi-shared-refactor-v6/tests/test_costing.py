from decimal import Decimal as D
import pytest
from app.services.costing import allocate_freight, line_unit_cost, split_return_discount, weighted_avg


def test_weighted_avg_basic():
    assert weighted_avg(10, 100, 10, 200) == D('150.0000')
    assert weighted_avg(0, 0, 5, 40) == D('40.0000')          # موجودی صفر: بهای ورودی
    assert weighted_avg(-3, 999, 5, 40) == D('40.0000')       # موجودی منفی وزن ندارد
    assert weighted_avg(3, 10, 1, 20) == D('12.5000')


def test_weighted_avg_rejects_nonpositive_qty():
    with pytest.raises(ValueError):
        weighted_avg(5, 10, 0, 10)


def test_allocate_freight_sums_exactly():
    parts = allocate_freight([D(100), D(100), D(100)], [1, 1, 1], D(100))
    assert sum(parts) == D(100) and parts[-1] == D('33.34')
    assert allocate_freight([D(300), D(100)], [1, 1], D(40)) == [D('30.00'), D('10.00')]


def test_allocate_freight_fallback_to_qty_and_zero():
    assert allocate_freight([D(0), D(0)], [3, 1], D(40)) == [D('30.00'), D('10.00')]
    assert allocate_freight([D(5)], [1], D(0)) == [D(0)]
    with pytest.raises(ValueError):
        allocate_freight([D(5)], [1], D(-1))


def test_line_unit_cost():
    # ۱۰ عدد × ۱۰۰ − تخفیف ۵۰ + حمل ۱۰۰ = ۱۰۵۰ → ۱۰۵ برای هر عدد
    assert line_unit_cost(10, D(1000), D(50), D(100)) == D('105.0000')


def test_split_return_discount():
    # قیمت ۱۰۰ × ۲ = ۲۰۰، مبلغ خالص ۱۸۰ → ۲۰ تخفیف
    assert split_return_discount(100, 2, D(180)) == D(20)
    assert split_return_discount(100, 2, D(200)) == D(0)
    assert split_return_discount(100, 2, D(205)) == D(0)


from app.services.costing import weighted_avg_out


def test_weighted_avg_out_keeps_value_consistent():
    # ۲۰ واحد با میانگین ۱۵۰ (ارزش ۳۰۰۰)؛ برگشت ۵ واحد با بهای رسید ۲۰۰ → ارزش ۲۰۰۰ روی ۱۵ واحد
    assert weighted_avg_out(20, 150, 5, 200) == D('133.3333')
    assert weighted_avg_out(20, 150, 4, 100) == D('162.5000')
    assert weighted_avg_out(10, 100, 4, 100) == D('100.0000')     # برگشت با همان میانگین: بدون تغییر


def test_weighted_avg_out_edge_cases():
    assert weighted_avg_out(5, 80, 5, 80) == D('80.0000')         # چیزی نمی‌ماند: میانگین قبلی
    assert weighted_avg_out(3, 80, 5, 80) == D('80.0000')         # موجودی کمتر از برگشت (داده‌ی ناسازگار)
    assert weighted_avg_out(10, 10, 2, 100) == D('10.0000')       # نتیجهٔ منفی → دست‌نخورده
    with pytest.raises(ValueError):
        weighted_avg_out(5, 10, 0, 10)
