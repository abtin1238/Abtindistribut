"""سند اختتامیه‌ی سال مالی: بستن حساب‌های درآمد/هزینه‌ی دوره به «سود (زیان) انباشته» (۳۲۰۰)."""
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D, audit, same_company
from app.core.config import utcnow
from app.models import FiscalPeriod, JournalEntry
from app.services.accounting import Q2, RETAINED, _jl_q, entry_dict, post_entry


def close_entry(pid: int, ctx, s: Session):
    u, cid, r = ctx; p = same_company(s, FiscalPeriod, pid, cid)
    if p.closed: raise HTTPException(409, 'دوره بسته است؛ ابتدا آن را باز کنید')
    for e in s.scalars(select(JournalEntry).where(JournalEntry.company_id == cid, JournalEntry.source_type == 'year_close', JournalEntry.source_id == p.id)):
        if not s.scalar(select(JournalEntry.id).where(JournalEntry.reverses_id == e.id)): raise HTTPException(409, 'سند اختتامیه‌ی این دوره قبلاً صادر شده است؛ برای صدور مجدد ابتدا آن را معکوس کنید')
    lines = []; dr = cr = Decimal(0)
    for c, n, ty, d, k in s.execute(_jl_q(cid, ['revenue', 'expense'], p.start_date, p.end_date)):
        net = (D(d) - D(k)).quantize(Q2)
        if net > 0: lines.append({'code': c, 'credit': net}); cr += net
        elif net < 0: lines.append({'code': c, 'debit': -net}); dr += -net
    if not lines: raise HTTPException(400, 'مانده‌ای در حساب‌های درآمد و هزینه‌ی این دوره نیست')
    profit = dr - cr
    lines.append({'code': RETAINED, 'credit': profit} if profit > 0 else {'code': RETAINED, 'debit': -profit})
    if profit == 0: lines.pop()
    e = post_entry(s, cid, u.id, f'سند اختتامیه {p.name}', lines, source=('year_close', p.id), entry_date=min(p.end_date, utcnow().date()))
    audit(s, cid, u.id, 'closing_entry', 'fiscal_period', p.id, {'profit': str(profit)}); s.commit()
    return {**entry_dict(s, e), 'net_profit': profit}
