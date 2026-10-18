"""عملیات تکمیلی انبار: گردش/کاردکس، بچ و انقضا، ارزش‌گذاری و تطبیق با دفتر، انبارگردانی."""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import D, Q2, audit, num, obj
from app.core.config import utcnow
from app.core.security import wh_check, wh_scope
from app.models import Account, JournalLine, Product, Stock, StockBatch, StockCount, StockCountLine, StockMove, User, Warehouse
from app.services.accounting import INVT, post_stock_adjust
from app.services.stock_batches import batched_qty, consume_batches
from .schemas import CountApproveIn, CountIn, CountLinesIn, LocationIn

IN_KINDS = {'in', 'purchase_in', 'return_in', 'transfer_in', 'transfer_cancel', 'count_in'}
OUT_KINDS = {'out', 'purchase_return', 'transfer_out', 'count_out'}
EXPIRY_SOON_DAYS = 30


def signed(kind: str, q) -> Decimal:
    return D(q) if kind in IN_KINDS else -D(q) if kind in OUT_KINDS else Decimal(0)


def _wh_filter(q, col, s, ctx, warehouse_id):
    if warehouse_id is not None:
        wh_check(s, ctx, warehouse_id); return q.where(col == warehouse_id)
    sc = wh_scope(s, ctx)
    return q if sc is None else q.where(col.in_(sc))


def _product(s, cid, pid) -> Product:
    p = s.get(Product, pid)
    if not p or p.company_id != cid: raise HTTPException(404, 'کالا یافت نشد')
    return p


def set_location(sid: int, x: LocationIn, ctx, s: Session):
    u, cid, r = ctx; st = s.get(Stock, sid)
    w = s.get(Warehouse, st.warehouse_id) if st else None
    if not st or not w or w.company_id != cid: raise HTTPException(404, 'ردیف موجودی یافت نشد')
    wh_check(s, ctx, w.id); st.location = x.location.strip()
    audit(s, cid, u.id, 'set_location', 'stock', st.id, {'location': st.location}); s.commit(); return obj(st)


# ───────────── گردش و کاردکس ─────────────
def moves(response: Response, limit: int, offset: int, warehouse_id: Optional[int], product_id: Optional[int], kind: Optional[str], start: Optional[date], end: Optional[date], ctx, s: Session):
    cid = ctx[1]
    q = select(StockMove, Product.name, Product.sku, Warehouse.name, User.name).join(Product, Product.id == StockMove.product_id).join(Warehouse, Warehouse.id == StockMove.warehouse_id).join(User, User.id == StockMove.user_id, isouter=True).where(StockMove.company_id == cid)
    q = _wh_filter(q, StockMove.warehouse_id, s, ctx, warehouse_id)
    if product_id is not None: q = q.where(StockMove.product_id == product_id)
    if kind: q = q.where(StockMove.kind == kind)
    if start: q = q.where(func.date(StockMove.created_at) >= start)
    if end: q = q.where(func.date(StockMove.created_at) <= end)
    total = s.scalar(select(func.count()).select_from(q.subquery()))
    response.headers['X-Total-Count'] = str(total)
    rows = s.execute(q.order_by(StockMove.id.desc()).limit(max(1, min(limit, 1000))).offset(max(0, offset))).all()
    return [{**obj(m), 'product': pn, 'sku': sku, 'warehouse': wn, 'user': un, 'direction': 'in' if m.kind in IN_KINDS else 'out'} for m, pn, sku, wn, un in rows]


def kardex(product_id: int, warehouse_id: Optional[int], start: Optional[date], end: Optional[date], ctx, s: Session):
    cid = ctx[1]; p = _product(s, cid, product_id)
    if start and end and start > end: raise HTTPException(400, 'بازه‌ی تاریخ نامعتبر است')
    base = _wh_filter(select(StockMove).where(StockMove.company_id == cid, StockMove.product_id == product_id), StockMove.warehouse_id, s, ctx, warehouse_id)
    opening = Decimal(0)
    if start:
        for m in s.scalars(base.where(func.date(StockMove.created_at) < start)): opening += signed(m.kind, m.quantity)
    q = base
    if start: q = q.where(func.date(StockMove.created_at) >= start)
    if end: q = q.where(func.date(StockMove.created_at) <= end)
    users = {}
    rows = []; bal = opening; tin = tout = Decimal(0)
    for m in s.scalars(q.order_by(StockMove.created_at, StockMove.id)):
        d = signed(m.kind, m.quantity); bal += d
        if d > 0: tin += d
        else: tout += -d
        if m.user_id not in users: u = s.get(User, m.user_id); users[m.user_id] = u.name if u else ''
        rows.append({'id': m.id, 'at': m.created_at, 'warehouse_id': m.warehouse_id, 'kind': m.kind, 'reference': m.reference, 'reason': m.reason, 'user': users[m.user_id], 'qty_in': d if d > 0 else Decimal(0), 'qty_out': -d if d < 0 else Decimal(0), 'balance': bal, 'unit_cost': m.unit_cost})
    out = {'product': {'id': p.id, 'name': p.name, 'sku': p.sku, 'unit': p.unit}, 'warehouse_id': warehouse_id, 'opening': opening, 'total_in': tin, 'total_out': tout, 'closing': bal, 'rows': rows}
    if not start and not end:  # مجموع گردش باید با موجودی فعلی برابر باشد (کنترل صحت)
        cur = D(s.scalar(_wh_filter(select(func.coalesce(func.sum(Stock.quantity), 0)).where(Stock.product_id == product_id), Stock.warehouse_id, s, ctx, warehouse_id)))
        out['stock_now'] = cur; out['matches_stock'] = cur == bal
    return out


# ───────────── بچ و انقضا ─────────────
def _batch_row(b: StockBatch, p: Product, w: Warehouse, today: date):
    days = (b.expiry_date - today).days if b.expiry_date else None
    st = 'no_expiry' if days is None else 'expired' if days < 0 else 'expiring' if days <= EXPIRY_SOON_DAYS else 'ok'
    return {'id': b.id, 'warehouse_id': b.warehouse_id, 'warehouse': w.name, 'product_id': b.product_id, 'product': p.name, 'sku': p.sku, 'batch_no': b.batch_no, 'expiry_date': b.expiry_date, 'days_to_expiry': days, 'quantity': b.quantity, 'status': st}


def batches(warehouse_id: Optional[int], product_id: Optional[int], include_empty: bool, ctx, s: Session):
    cid = ctx[1]; q = select(StockBatch, Product, Warehouse).join(Product, Product.id == StockBatch.product_id).join(Warehouse, Warehouse.id == StockBatch.warehouse_id).where(StockBatch.company_id == cid)
    q = _wh_filter(q, StockBatch.warehouse_id, s, ctx, warehouse_id)
    if product_id is not None: q = q.where(StockBatch.product_id == product_id)
    if not include_empty: q = q.where(StockBatch.quantity > 0)
    today = utcnow().date()
    return [_batch_row(b, p, w, today) for b, p, w in s.execute(q.order_by(StockBatch.expiry_date.is_(None), StockBatch.expiry_date, StockBatch.id))]


def expiring(days: int, warehouse_id: Optional[int], ctx, s: Session):
    """بچ‌های دارای موجودی که تا `days` روز دیگر منقضی می‌شوند یا منقضی شده‌اند (ارزش ریالی با بهای میانگین)"""
    cid = ctx[1]; today = utcnow().date(); lim = today + timedelta(days=max(0, min(days, 3650)))
    q = select(StockBatch, Product, Warehouse).join(Product, Product.id == StockBatch.product_id).join(Warehouse, Warehouse.id == StockBatch.warehouse_id).where(StockBatch.company_id == cid, StockBatch.quantity > 0, StockBatch.expiry_date.is_not(None), StockBatch.expiry_date <= lim)
    q = _wh_filter(q, StockBatch.warehouse_id, s, ctx, warehouse_id)
    items = []
    for b, p, w in s.execute(q.order_by(StockBatch.expiry_date, StockBatch.id)):
        r = _batch_row(b, p, w, today); r['value'] = (D(b.quantity) * D(p.avg_cost)).quantize(Q2); items.append(r)
    return {'days': days, 'items': items, 'expired_count': sum(1 for x in items if x['status'] == 'expired'), 'total_value': sum((x['value'] for x in items), Decimal(0))}


# ───────────── ارزش‌گذاری و تطبیق با دفتر کل ─────────────
def valuation(warehouse_id: Optional[int], ctx, s: Session):
    cid = ctx[1]
    q = select(Product, func.coalesce(func.sum(Stock.quantity), 0), func.coalesce(func.sum(Stock.reserved), 0)).join(Stock, Stock.product_id == Product.id).join(Warehouse, Warehouse.id == Stock.warehouse_id).where(Product.company_id == cid, Warehouse.company_id == cid)
    q = _wh_filter(q, Stock.warehouse_id, s, ctx, warehouse_id)
    rows = []
    for p, qty, res in s.execute(q.group_by(Product.id).order_by(Product.name)):
        qty = D(qty); v = (qty * D(p.avg_cost)).quantize(Q2)
        rows.append({'product_id': p.id, 'product': p.name, 'sku': p.sku, 'unit': p.unit, 'quantity': qty, 'reserved': D(res), 'avg_cost': p.avg_cost, 'value': v, 'uncosted': qty > 0 and D(p.avg_cost) == 0})
    total = sum((x['value'] for x in rows), Decimal(0))
    out = {'items': rows, 'total_value': total, 'uncosted_products': sum(1 for x in rows if x['uncosted'])}
    if warehouse_id is None and wh_scope(s, ctx) is None:  # تطبیق انبار با حساب موجودی کالا (1310)
        a = s.scalar(select(Account.id).where(Account.company_id == cid, Account.code == INVT))
        led = Decimal(0)
        if a:
            d, c = s.execute(select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0)).where(JournalLine.company_id == cid, JournalLine.account_id == a)).one(); led = D(d) - D(c)
        diff = led - total
        out.update({'ledger_balance': led, 'difference': diff, 'reconciled': abs(diff) <= Decimal('0.5') * max(len(rows), 1)})
    return out


# ───────────── انبارگردانی ─────────────
def _count(s, cid, id_) -> StockCount:
    c = s.get(StockCount, id_, with_for_update=True)
    if not c or c.company_id != cid: raise HTTPException(404, 'برگه‌ی انبارگردانی یافت نشد')
    return c


def count_create(x: CountIn, ctx, s: Session):
    u, cid, r = ctx; w = s.get(Warehouse, x.warehouse_id)
    if not w or w.company_id != cid: raise HTTPException(404, 'انبار یافت نشد')
    wh_check(s, ctx, w.id)
    if s.scalar(select(StockCount.id).where(StockCount.warehouse_id == w.id, StockCount.status.in_(('draft', 'counting')))): raise HTTPException(409, 'برای این انبار برگه‌ی انبارگردانی باز وجود دارد')
    q = select(Stock).where(Stock.warehouse_id == w.id).with_for_update()
    if x.product_ids is not None:
        ids = set(x.product_ids)
        if not ids: raise HTTPException(400, 'فهرست کالا خالی است')
        ps = {p.id for p in s.scalars(select(Product).where(Product.id.in_(ids), Product.company_id == cid))}
        if ps != ids: raise HTTPException(404, 'کالای نامعتبر در فهرست')
        q = q.where(Stock.product_id.in_(ids))
    sts = s.scalars(q).all(); have = {st.product_id: D(st.quantity) for st in sts}
    if x.product_ids is not None:
        for pid in x.product_ids: have.setdefault(pid, Decimal(0))
    if not have: raise HTTPException(400, 'کالایی برای شمارش در این انبار نیست')
    c = StockCount(company_id=cid, number=num('CNT', StockCount, s), warehouse_id=w.id, note=x.note, created_by=u.id); s.add(c); s.flush()
    for pid, q_ in sorted(have.items()): s.add(StockCountLine(count_id=c.id, product_id=pid, system_qty=q_))
    audit(s, cid, u.id, 'create', 'stock_count', c.id, {'warehouse_id': w.id, 'lines': len(have)}); s.commit(); return count_get(c.id, ctx, s)


def count_get(id_: int, ctx, s: Session):
    cid = ctx[1]; c = s.get(StockCount, id_)
    if not c or c.company_id != cid: raise HTTPException(404, 'برگه‌ی انبارگردانی یافت نشد')
    wh_check(s, ctx, c.warehouse_id)
    lines = []; tdiff = Decimal(0)
    for l, p in s.execute(select(StockCountLine, Product).join(Product, Product.id == StockCountLine.product_id).where(StockCountLine.count_id == c.id).order_by(Product.name)):
        diff = None if l.counted_qty is None else D(l.counted_qty) - D(l.system_qty); val = None if diff is None else (diff * D(p.avg_cost)).quantize(Q2)
        if val is not None: tdiff += val
        lines.append({'product_id': p.id, 'product': p.name, 'sku': p.sku, 'unit': p.unit, 'system_qty': l.system_qty, 'counted_qty': l.counted_qty, 'difference': diff, 'avg_cost': p.avg_cost, 'value_difference': val})
    return {**obj(c), 'lines': lines, 'counted_lines': sum(1 for x in lines if x['counted_qty'] is not None), 'total_value_difference': tdiff}


def count_list(ctx, s: Session):
    cid = ctx[1]; sc = wh_scope(s, ctx)
    return [obj(c) for c in s.scalars(select(StockCount).where(StockCount.company_id == cid).order_by(StockCount.id.desc()).limit(500)) if sc is None or c.warehouse_id in sc]


def count_set_lines(id_: int, x: CountLinesIn, ctx, s: Session):
    u, cid, r = ctx; c = _count(s, cid, id_); wh_check(s, ctx, c.warehouse_id)
    if c.status not in ('draft', 'counting'): raise HTTPException(409, 'این برگه دیگر قابل ویرایش نیست')
    by = {l.product_id: l for l in s.scalars(select(StockCountLine).where(StockCountLine.count_id == c.id).with_for_update())}
    for li in x.lines:
        if li.product_id not in by: raise HTTPException(400, 'کالا در این برگه نیست')
        by[li.product_id].counted_qty = li.counted_qty
    c.status = 'counting'; audit(s, cid, u.id, 'count', 'stock_count', c.id, {'lines': len(x.lines)}); s.commit(); return count_get(c.id, ctx, s)


def count_approve(id_: int, x: CountApproveIn, ctx, s: Session):
    """اختلاف شمارش با عکس اولیه‌ی موجودی اعمال می‌شود (نه با موجودی لحظه‌ی تأیید) تا حرکت‌های هم‌زمان گم نشوند."""
    u, cid, r = ctx; c = _count(s, cid, id_); wh_check(s, ctx, c.warehouse_id)
    if c.status != 'counting': raise HTTPException(409, 'فقط برگه‌ی در حال شمارش قابل تأیید است')
    lines = s.scalars(select(StockCountLine).where(StockCountLine.count_id == c.id)).all(); done = [l for l in lines if l.counted_qty is not None]
    if not done: raise HTTPException(400, 'هیچ کالایی شمارش نشده است')
    reason = (x.reason or '').strip() or f'انبارگردانی {c.number}'; adjusted = 0; value = Decimal(0)
    for l in done:
        delta = D(l.counted_qty) - D(l.system_qty)
        if delta == 0: continue
        p = s.get(Product, l.product_id, with_for_update=True)
        st = s.scalar(select(Stock).where(Stock.warehouse_id == c.warehouse_id, Stock.product_id == l.product_id).with_for_update()) or Stock(warehouse_id=c.warehouse_id, product_id=l.product_id, quantity=0, reserved=0)
        s.add(st); newq = D(st.quantity) + delta
        if newq < 0 or newq < D(st.reserved): raise HTTPException(409, f'اعمال شمارش «{p.name}» موجودی را کمتر از رزرو/صفر می‌کند؛ ابتدا رزروها را بررسی کنید')
        st.quantity = newq
        s.add(StockMove(company_id=cid, warehouse_id=c.warehouse_id, product_id=l.product_id, kind='count_in' if delta > 0 else 'count_out', quantity=abs(delta), unit_cost=p.avg_cost if D(p.avg_cost) else None, reference=c.number, reason=reason[:200], user_id=u.id))
        if delta < 0: consume_batches(s, cid, c.warehouse_id, l.product_id, -delta)
        value += post_stock_adjust(s, cid, u.id, p, delta, c.number) * (1 if delta > 0 else -1); adjusted += 1
    c.status = 'approved'; c.approved_by = u.id; c.approved_at = utcnow()
    audit(s, cid, u.id, 'approve', 'stock_count', c.id, {'adjusted': adjusted, 'value': str(value)}); s.commit()
    return {**count_get(c.id, ctx, s), 'adjusted_lines': adjusted, 'ledger_value_change': value}


def count_cancel(id_: int, ctx, s: Session):
    u, cid, r = ctx; c = _count(s, cid, id_); wh_check(s, ctx, c.warehouse_id)
    if c.status not in ('draft', 'counting'): raise HTTPException(409, 'این برگه قابل لغو نیست')
    c.status = 'cancelled'; audit(s, cid, u.id, 'cancel', 'stock_count', c.id); s.commit(); return obj(c)
