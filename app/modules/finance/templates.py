"""قالب‌های سندسازی (مثلاً «پرداخت اجاره»، «هزینه‌ی حمل»)."""
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D, Q2, audit, obj
from app.models import Account, JournalTemplate
from app.services.accounting import entry_dict, post_entry
from .schemas import JournalTemplateIn, TemplatePostIn


def _check_lines(s, cid, lines):
    for l in lines:
        a = s.scalar(select(Account).where(Account.company_id == cid, Account.code == l.account_code))
        if not a: raise HTTPException(404, f'حساب {l.account_code} یافت نشد')
        if a.level < 3 or not a.active: raise HTTPException(400, f'حساب {l.account_code} قابل ثبت سند نیست')
    if sum((D(l.ratio) for l in lines if l.side == 'debit'), Decimal(0)) != sum((D(l.ratio) for l in lines if l.side == 'credit'), Decimal(0)):
        raise HTTPException(400, 'جمع ضرایب بدهکار و بستانکار قالب برابر نیست')


def tlist(ctx, s: Session):
    return [obj(t) for t in s.scalars(select(JournalTemplate).where(JournalTemplate.company_id == ctx[1]).order_by(JournalTemplate.name))]


def tadd(x: JournalTemplateIn, ctx, s: Session):
    u, cid, r = ctx; _check_lines(s, cid, x.lines)
    if s.scalar(select(JournalTemplate.id).where(JournalTemplate.company_id == cid, JournalTemplate.name == x.name.strip())): raise HTTPException(409, 'نام قالب تکراری است')
    t = JournalTemplate(company_id=cid, name=x.name.strip(), description=x.description, lines=[{'account_code': l.account_code, 'side': l.side, 'ratio': str(l.ratio), 'memo': l.memo} for l in x.lines], created_by=u.id)
    s.add(t); s.flush(); audit(s, cid, u.id, 'create', 'journal_template', t.id, {'name': t.name}); s.commit(); return obj(t)


def tdelete(tid: int, ctx, s: Session):
    u, cid, r = ctx; t = s.get(JournalTemplate, tid)
    if not t or t.company_id != cid: raise HTTPException(404, 'قالب یافت نشد')
    s.delete(t); audit(s, cid, u.id, 'delete', 'journal_template', tid, {}); s.commit(); return {'ok': True}


def tpost(tid: int, x: TemplatePostIn, ctx, s: Session):
    u, cid, r = ctx; t = s.get(JournalTemplate, tid)
    if not t or t.company_id != cid: raise HTTPException(404, 'قالب یافت نشد')
    L = []
    for l in t.lines:
        amt = (D(x.amount) * D(l['ratio'])).quantize(Q2)
        L.append({'code': l['account_code'], 'debit' if l['side'] == 'debit' else 'credit': amt, 'memo': l.get('memo', '')})
    e = post_entry(s, cid, u.id, x.description.strip() or t.name, L, source=('manual', None), entry_date=x.entry_date)
    audit(s, cid, u.id, 'post', 'journal_template', t.id, {'amount': str(x.amount), 'entry': e.id}); s.commit(); return entry_dict(s, e)
