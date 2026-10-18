from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import BankAccountIn, BankAccountPatch, BankTransferIn, ChequebookIn, ChequebookPatch, LeafVoidIn
from .service import accounts as _s_accounts, add_account as _s_add_account, edit_account as _s_edit_account, statement as _s_statement, transfer as _s_transfer, books as _s_books, add_book as _s_add_book, set_book_status as _s_set_book_status, leaves as _s_leaves, void_leaf as _s_void_leaf, checks_due as _s_checks_due, check_history as _s_check_history

router=APIRouter()

@router.get('/api/bank-accounts')
def accounts(ctx=Depends(current), s: Session=Depends(db)):
 return _s_accounts(ctx=ctx, s=s)

@router.post('/api/bank-accounts')
def add_account(x: BankAccountIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_account(x=x, ctx=ctx, s=s)

@router.patch('/api/bank-accounts/{bid}')
def edit_account(bid: int, x: BankAccountPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_edit_account(bid=bid, x=x, ctx=ctx, s=s)

@router.get('/api/bank-accounts/{bid}/statement')
def statement(bid: int, start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_statement(bid=bid, start=start, end=end, ctx=ctx, s=s)

@router.post('/api/bank-transfers')
def transfer(x: BankTransferIn, ctx=Depends(current), s: Session=Depends(db)):
 'from/to خالی = صندوق. سند: بدهکار مقصد / بستانکار مبدأ؛ از حساب بانکی بیش از مانده برداشت نمی\u200cشود'
 return _s_transfer(x=x, ctx=ctx, s=s)

@router.get('/api/chequebooks')
def books(bank_account_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_books(bank_account_id=bank_account_id, ctx=ctx, s=s)

@router.post('/api/chequebooks')
def add_book(x: ChequebookIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_book(x=x, ctx=ctx, s=s)

@router.patch('/api/chequebooks/{bid}')
def set_book_status(bid: int, x: ChequebookPatch, ctx=Depends(current), s: Session=Depends(db)):
 'active ↔ cancelled (دسته\u200cچک گم\u200cشده/مسدود)؛ «تمام\u200cشده» فقط خودکار با مصرف آخرین برگ'
 return _s_set_book_status(bid=bid, x=x, ctx=ctx, s=s)

@router.get('/api/chequebooks/{bid}/leaves')
def leaves(bid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_leaves(bid=bid, ctx=ctx, s=s)

@router.post('/api/chequebooks/{bid}/void-leaf')
def void_leaf(bid: int, x: LeafVoidIn, ctx=Depends(current), s: Session=Depends(db)):
 'باطل\u200cکردن برگ سفید (خراب/گم\u200cشده)؛ برگ مصرف\u200cشده حساب می\u200cشود و سند مالی ندارد'
 return _s_void_leaf(bid=bid, x=x, ctx=ctx, s=s)

@router.get('/api/checks/due')
def checks_due(days: int=Query(7, ge=0, le=365), ctx=Depends(current), s: Session=Depends(db)):
 'چک\u200cهای باز (در انتظار/ایداع\u200cشده) با سررسید تا `days` روز دیگر + سررسیدگذشته\u200cها؛ هشدار برای پیگیری'
 return _s_checks_due(days=days, ctx=ctx, s=s)

@router.get('/api/checks/{chk}/history')
def check_history(chk: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_check_history(chk=chk, ctx=ctx, s=s)

from app.schemas import BankChargeIn, ReconcileIn
from . import reconcile as rc

@router.post('/api/bank-accounts/{bid}/charges')
def bank_charge(bid: int, x: BankChargeIn, ctx=Depends(current), s: Session=Depends(db)):
 return rc.charge(bid, x, ctx, s)

@router.get('/api/bank-accounts/{bid}/reconcile')
def bank_reconcile_open(bid: int, ctx=Depends(current), s: Session=Depends(db)):
 return rc.open_lines(bid, ctx, s)

@router.post('/api/bank-accounts/{bid}/reconcile')
def bank_reconcile(bid: int, x: ReconcileIn, ctx=Depends(current), s: Session=Depends(db)):
 return rc.reconcile(bid, x, ctx, s)

@router.get('/api/bank-accounts/{bid}/reconciliations')
def bank_reconciliations(bid: int, ctx=Depends(current), s: Session=Depends(db)):
 return rc.history(bid, ctx, s)

@router.delete('/api/bank-accounts/{bid}/reconciliations/{rid}')
def bank_reconcile_undo(bid: int, rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return rc.undo(bid, rid, ctx, s)
