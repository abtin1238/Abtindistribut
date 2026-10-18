"""کدینگ سلسله‌مراتبی حساب‌ها: ۱ گروه، ۲ کل، ۳ معین، ۴ تفصیلی. ثبت سند فقط روی سطح ≥ ۳."""
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.common import D, audit, obj
from app.models import Account, JournalLine
from app.services.accounting import ACCOUNT_TYPES, CHART
from .schemas import AccountIn, AccountPatch

GROUPS = {'1': ('دارایی‌ها', 'asset'), '2': ('بدهی‌ها', 'liability'), '3': ('حقوق صاحبان سرمایه', 'equity'), '4': ('درآمدها', 'revenue'), '5': ('هزینه‌ها', 'expense'),
          '11': ('وجوه نقد و بانک', 'asset'), '12': ('مطالبات', 'asset'), '13': ('موجودی‌ها', 'asset'), '21': ('بدهی‌های تجاری', 'liability'), '22': ('مالیات‌ها', 'liability'), '23': ('بدهی‌های پرسنلی', 'liability'),
          '31': ('سرمایه و مانده اول دوره', 'equity'), '41': ('درآمد عملیاتی', 'revenue'), '42': ('درآمدهای غیرعملیاتی', 'revenue'), '51': ('بهای تمام‌شده', 'expense'), '52': ('تعدیلات انبار', 'expense'), '53': ('هزینه‌های پرسنلی', 'expense'), '54': ('هزینه‌های مالی و بانکی', 'expense')}


def _parent(s, cid, code, typ):
    for n in range(len(code) - 1, 0, -1):
        p = s.scalar(select(Account).where(Account.company_id == cid, Account.code == code[:n]))
        if p and p.type == typ and p.level < 4: return p
    return None


def ensure_chart(s: Session, cid: int):
    have = {a.code: a for a in s.scalars(select(Account).where(Account.company_id == cid))}
    for c, (n, t) in sorted(GROUPS.items(), key=lambda kv: len(kv[0])):
        if c not in have:
            a = Account(company_id=cid, code=c, name=n, type=t, level=len(c)); s.add(a); s.flush(); have[c] = a
    for c, (n, ty) in CHART.items():
        if c not in have:
            a = Account(company_id=cid, code=c, name=n, type=ty, level=3); s.add(a); s.flush(); have[c] = a
    for a in sorted(have.values(), key=lambda x: len(x.code)):
        if a.code in GROUPS:
            if len(a.code) == 2 and a.parent_id is None and a.code[0] in have: a.parent_id = have[a.code[0]].id
            continue
        if a.parent_id is not None: continue
        p = _parent(s, cid, a.code, a.type)
        if p: a.parent_id = p.id; a.level = min(4, p.level + 1) if p.level >= 3 else 3
        elif a.code[:2] in have and a.type == have[a.code[:2]].type: a.parent_id = have[a.code[:2]].id
    s.flush()


def tree(ctx, s: Session):
    cid = ctx[1]; ensure_chart(s, cid); s.commit()
    sums = {i: (D(d), D(c)) for i, d, c in s.execute(select(JournalLine.account_id, func.sum(JournalLine.debit), func.sum(JournalLine.credit)).where(JournalLine.company_id == cid).group_by(JournalLine.account_id))}
    accs = s.scalars(select(Account).where(Account.company_id == cid).order_by(Account.code)).all()
    nodes = {a.id: {**obj(a), 'debit': sums.get(a.id, (Decimal(0), Decimal(0)))[0], 'credit': sums.get(a.id, (Decimal(0), Decimal(0)))[1], 'children': []} for a in accs}
    roots = []
    for a in accs:
        n = nodes[a.id]; (nodes[a.parent_id]['children'] if a.parent_id in nodes else roots).append(n)
    def roll(n):
        td, tc = n['debit'], n['credit']
        for ch in n['children']: d, c = roll(ch); td += d; tc += c
        n['total_debit'], n['total_credit'], n['total_balance'], n['balance'] = td, tc, td - tc, n['debit'] - n['credit']; return td, tc
    for r in roots: roll(r)
    return roots


def add(x: AccountIn, ctx, s: Session):
    u, cid, r = ctx
    if x.type not in ACCOUNT_TYPES: raise HTTPException(400, 'نوع حساب نامعتبر است')
    if s.scalar(select(Account.id).where(Account.company_id == cid, Account.code == x.code)): raise HTTPException(409, 'کد حساب تکراری است')
    ensure_chart(s, cid)
    if x.parent_code:
        p = s.scalar(select(Account).where(Account.company_id == cid, Account.code == x.parent_code))
        if not p: raise HTTPException(404, 'حساب والد یافت نشد')
        if p.type != x.type: raise HTTPException(400, 'نوع حساب با والد یکسان نیست')
        if not x.code.startswith(p.code) or len(x.code) <= len(p.code): raise HTTPException(400, 'کد حساب باید با کد والد شروع شود و بلندتر باشد')
        if p.level >= 4: raise HTTPException(400, 'حداکثر ۴ سطح (گروه، کل، معین، تفصیلی)')
    else: p = _parent(s, cid, x.code, x.type)
    lvl = 3 if not p else (p.level + 1 if p.level >= 3 else 3)
    q = Account(company_id=cid, code=x.code, name=x.name, type=x.type, parent_id=p.id if p else None, level=lvl); s.add(q)
    audit(s, cid, u.id, 'create', 'account', None, x.model_dump()); s.commit(); s.refresh(q); return obj(q)


def patch(aid: int, x: AccountPatch, ctx, s: Session):
    u, cid, r = ctx; a = s.get(Account, aid)
    if not a or a.company_id != cid: raise HTTPException(404, 'حساب یافت نشد')
    if x.name is not None: a.name = x.name.strip()
    if x.active is False and a.active:
        if a.code in CHART or a.code in GROUPS: raise HTTPException(409, 'حساب سیستمی غیرفعال نمی‌شود')
        d, c = s.execute(select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0)).where(JournalLine.account_id == a.id)).one()
        if D(d) != D(c): raise HTTPException(409, 'حساب با مانده غیرصفر غیرفعال نمی‌شود')
        if s.scalar(select(Account.id).where(Account.parent_id == a.id, Account.active == True)): raise HTTPException(409, 'حساب زیرمجموعه‌ی فعال دارد')
    if x.active is not None: a.active = x.active
    audit(s, cid, u.id, 'update', 'account', a.id, x.model_dump(exclude_unset=True)); s.commit(); return obj(a)
