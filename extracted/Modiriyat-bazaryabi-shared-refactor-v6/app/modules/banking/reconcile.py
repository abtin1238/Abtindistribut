"""کارمزد/سود بانکی و مغایرت‌گیری با صورت‌حساب بانک."""
from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.common import D, audit, obj, same_company
from app.models import Account, BankAccount, BankReconciliation, BankReconciliationLine, JournalEntry, JournalLine
from app.services.accounting import BANK_FEE, BANK_INT, bank_balance, entry_dict, post_entry
from .schemas import BankChargeIn, ReconcileIn


def charge(bid: int, x: BankChargeIn, ctx, s: Session):
    """کارمزد: بدهکار ۵۴۰۰ / بستانکار بانک (بیش از مانده نمی‌شود). سود: بدهکار بانک / بستانکار ۴۲۱۰"""
    u, cid, r = ctx; b = same_company(s, BankAccount, bid, cid)
    if not b.active: raise HTTPException(409, 'حساب بانکی غیرفعال است')
    amt = D(x.amount)
    if x.kind == 'fee':
        if bank_balance(s, cid, b) < amt: raise HTTPException(409, 'موجودی حساب برای کارمزد کافی نیست')
        lines = [{'code': BANK_FEE, 'debit': amt}, {'code': b.ledger_code, 'credit': amt}]; d = f'کارمزد بانکی {b.name}'
    else:
        lines = [{'code': b.ledger_code, 'debit': amt}, {'code': BANK_INT, 'credit': amt}]; d = f'سود سپرده {b.name}'
    e = post_entry(s, cid, u.id, d + (f' — {x.note.strip()}' if x.note.strip() else ''), lines, source=('bank_charge', b.id))
    audit(s, cid, u.id, 'bank_charge', 'bank_account', b.id, x.model_dump(mode='json')); s.commit(); return entry_dict(s, e)


def _acct(s, cid, b):
    a = s.scalar(select(Account).where(Account.company_id == cid, Account.code == b.ledger_code))
    if not a: raise HTTPException(404, 'حساب دفتر کل بانک یافت نشد')
    return a


def _cleared(s, bid):
    d, c = s.execute(select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0)).join(BankReconciliationLine, BankReconciliationLine.journal_line_id == JournalLine.id).join(BankReconciliation, BankReconciliation.id == BankReconciliationLine.reconciliation_id).where(BankReconciliation.bank_account_id == bid)).one()
    return D(d) - D(c)


def open_lines(bid: int, ctx, s: Session):
    cid = ctx[1]; b = same_company(s, BankAccount, bid, cid); a = _acct(s, cid, b)
    done = select(BankReconciliationLine.journal_line_id)
    rows = [{'line_id': l.id, 'entry_id': e.id, 'number': e.number, 'date': e.entry_date, 'description': e.description, 'debit': l.debit, 'credit': l.credit} for l, e in s.execute(select(JournalLine, JournalEntry).join(JournalEntry, JournalEntry.id == JournalLine.entry_id).where(JournalLine.company_id == cid, JournalLine.account_id == a.id, JournalLine.id.not_in(done)).order_by(JournalEntry.id, JournalLine.id))]
    return {'account': {'id': b.id, 'name': b.name, 'ledger_code': b.ledger_code}, 'book_balance': bank_balance(s, cid, b), 'cleared_balance': _cleared(s, b.id), 'lines': rows,
            'in_transit_deposits': sum((D(x['debit']) for x in rows), Decimal(0)), 'outstanding_payments': sum((D(x['credit']) for x in rows), Decimal(0))}


def reconcile(bid: int, x: ReconcileIn, ctx, s: Session):
    """سطرهای انتخابی «تطبیق‌شده» می‌شوند؛ اختلاف = مانده‌ی صورت‌حساب − مانده‌ی سطرهای تطبیق‌شده (باید صفر شود)"""
    u, cid, r = ctx; b = same_company(s, BankAccount, bid, cid); a = _acct(s, cid, b)
    ids = set(x.line_ids)
    ls = s.scalars(select(JournalLine).where(JournalLine.id.in_(ids), JournalLine.company_id == cid, JournalLine.account_id == a.id).with_for_update()).all()
    if len(ls) != len(ids): raise HTTPException(400, 'سطر نامعتبر یا متعلق به حساب دیگر')
    if s.scalar(select(BankReconciliationLine.id).where(BankReconciliationLine.journal_line_id.in_(ids))): raise HTTPException(409, 'برخی سطرها قبلاً تطبیق داده شده‌اند')
    rec = BankReconciliation(company_id=cid, bank_account_id=b.id, statement_balance=x.statement_balance, cleared_balance=0, book_balance=bank_balance(s, cid, b), difference=0, note=x.note, created_by=u.id); s.add(rec); s.flush()
    for l in ls: s.add(BankReconciliationLine(reconciliation_id=rec.id, journal_line_id=l.id))
    s.flush(); rec.cleared_balance = _cleared(s, b.id); rec.difference = D(x.statement_balance) - D(rec.cleared_balance)
    audit(s, cid, u.id, 'reconcile', 'bank_account', b.id, {'reconciliation': rec.id, 'difference': str(rec.difference)}); s.commit()
    return {**obj(rec), 'balanced': D(rec.difference) == 0, 'lines': len(ls)}


def history(bid: int, ctx, s: Session):
    cid = ctx[1]; same_company(s, BankAccount, bid, cid)
    return [obj(r) | {'balanced': D(r.difference) == 0} for r in s.scalars(select(BankReconciliation).where(BankReconciliation.bank_account_id == bid).order_by(BankReconciliation.id.desc()))]


def undo(bid: int, rid: int, ctx, s: Session):
    u, cid, r = ctx; same_company(s, BankAccount, bid, cid)
    last = s.scalar(select(func.max(BankReconciliation.id)).where(BankReconciliation.bank_account_id == bid))
    rec = s.get(BankReconciliation, rid)
    if not rec or rec.bank_account_id != bid: raise HTTPException(404, 'مغایرت‌گیری یافت نشد')
    if rid != last: raise HTTPException(409, 'فقط آخرین مغایرت‌گیری قابل بازگشت است')
    for l in s.scalars(select(BankReconciliationLine).where(BankReconciliationLine.reconciliation_id == rid)): s.delete(l)
    s.flush(); s.delete(rec); audit(s, cid, u.id, 'undo_reconcile', 'bank_account', bid, {'reconciliation': rid}); s.commit(); return {'ok': True}
