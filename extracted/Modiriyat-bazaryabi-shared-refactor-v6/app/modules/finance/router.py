from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import AccountPatch, CheckEndorseIn, FiscalPeriodIn, AccountIn, CheckIn, CheckStatusIn, JournalIn, PaymentIn
from .service import payment as _s_payment, payments as _s_payments, checks as _s_checks, add_check as _s_add_check, update_check as _s_update_check, journal as _s_journal, journal_list as _s_journal_list, journal_get as _s_journal_get, journal_reverse as _s_journal_reverse, accounts_list as _s_accounts_list, account_add as _s_account_add, trial_balance as _s_trial_balance, profit_loss_monthly as _s_profit_loss_monthly, customer_ledger as _s_customer_ledger, profit_loss as _s_profit_loss, balance_sheet as _s_balance_sheet, general_ledger as _s_general_ledger, aging as _s_aging, trial_balance_xlsx as _s_trial_balance_xlsx, aging_xlsx as _s_aging_xlsx, profit_loss_xlsx as _s_profit_loss_xlsx, general_ledger_xlsx as _s_general_ledger_xlsx, fiscal_list as _s_fiscal_list, fiscal_create as _s_fiscal_create, fiscal_close as _s_fiscal_close, fiscal_reopen as _s_fiscal_reopen, endorse_check as _s_endorse_check

router=APIRouter()

@router.post('/api/payments')
def payment(x: PaymentIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_payment(x=x, ctx=ctx, s=s)

@router.get('/api/payments')
def payments(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_payments(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.get('/api/checks')
def checks(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_checks(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.post('/api/checks')
def add_check(x: CheckIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_check(x=x, ctx=ctx, s=s)

@router.patch('/api/checks/{cid}')
def update_check(cid: int, x: CheckStatusIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_update_check(cid=cid, x=x, ctx=ctx, s=s)

@router.post('/api/journal')
def journal(x: JournalIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_journal(x=x, ctx=ctx, s=s)

@router.get('/api/journal')
def journal_list(ctx=Depends(current), s: Session=Depends(db)):
 return _s_journal_list(ctx=ctx, s=s)

@router.get('/api/journal/{eid}')
def journal_get(eid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_journal_get(eid=eid, ctx=ctx, s=s)

@router.post('/api/journal/{eid}/reverse')
def journal_reverse(eid: int, reason: str='', ctx=Depends(current), s: Session=Depends(db)):
 return _s_journal_reverse(eid=eid, reason=reason, ctx=ctx, s=s)

@router.get('/api/accounts')
def accounts_list(ctx=Depends(current), s: Session=Depends(db)):
 return _s_accounts_list(ctx=ctx, s=s)

@router.post('/api/accounts')
def account_add(x: AccountIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_account_add(x=x, ctx=ctx, s=s)

@router.get('/api/reports/trial-balance')
def trial_balance(ctx=Depends(current), s: Session=Depends(db)):
 return _s_trial_balance(ctx=ctx, s=s)

@router.get('/api/reports/profit-loss/monthly')
def profit_loss_monthly(months: int=Query(12, ge=1, le=24), ctx=Depends(current), s: Session=Depends(db)):
 'روند ماهانه\u200cی درآمد/هزینه بر اساس ماه شمسی (از اسناد ثبت\u200cشده)؛ مجوز finance.read از پیشوند مسیر'
 return _s_profit_loss_monthly(months=months, ctx=ctx, s=s)

@router.get('/api/customers/{customer_id}/ledger')
def customer_ledger(customer_id: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_customer_ledger(customer_id=customer_id, ctx=ctx, s=s)

@router.get('/api/reports/profit-loss')
def profit_loss(start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_profit_loss(start=start, end=end, ctx=ctx, s=s)

@router.get('/api/reports/balance-sheet')
def balance_sheet(end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_balance_sheet(end=end, ctx=ctx, s=s)

@router.get('/api/reports/general-ledger')
def general_ledger(account_code: str, start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_general_ledger(account_code=account_code, start=start, end=end, ctx=ctx, s=s)

@router.get('/api/reports/aging')
def aging(as_of: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_aging(as_of=as_of, ctx=ctx, s=s)

@router.get('/api/reports/trial-balance.xlsx')
def trial_balance_xlsx(ctx=Depends(current), s: Session=Depends(db)):
 return _s_trial_balance_xlsx(ctx=ctx, s=s)

@router.get('/api/reports/aging.xlsx')
def aging_xlsx(as_of: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_aging_xlsx(as_of=as_of, ctx=ctx, s=s)

@router.get('/api/reports/profit-loss.xlsx')
def profit_loss_xlsx(start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_profit_loss_xlsx(start=start, end=end, ctx=ctx, s=s)

@router.get('/api/reports/general-ledger.xlsx')
def general_ledger_xlsx(account_code: str, start: Optional[date]=Query(None), end: Optional[date]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_general_ledger_xlsx(account_code=account_code, start=start, end=end, ctx=ctx, s=s)

@router.get('/api/fiscal/periods')
def fiscal_list(ctx=Depends(current), s: Session=Depends(db)):
 return _s_fiscal_list(ctx=ctx, s=s)

@router.post('/api/fiscal/periods')
def fiscal_create(x: FiscalPeriodIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_fiscal_create(x=x, ctx=ctx, s=s)

@router.post('/api/fiscal/periods/{pid}/close')
def fiscal_close(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_fiscal_close(pid=pid, ctx=ctx, s=s)

@router.post('/api/fiscal/periods/{pid}/reopen')
def fiscal_reopen(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_fiscal_reopen(pid=pid, ctx=ctx, s=s)

@router.post('/api/checks/{chk}/endorse')
def endorse_check(chk: int, x: CheckEndorseIn, ctx=Depends(current), s: Session=Depends(db)):
 'خرج چک دریافتی به تأمین\u200cکننده: بدهی تأمین\u200cکننده کم و اسناد دریافتنی بسته می\u200cشود'
 return _s_endorse_check(chk=chk, x=x, ctx=ctx, s=s)

@router.get('/api/accounts/tree')
def accounts_tree(ctx=Depends(current), s: Session=Depends(db)):
 from . import chart
 return chart.tree(ctx, s)

@router.patch('/api/accounts/{aid}')
def account_patch(aid: int, x: AccountPatch, ctx=Depends(current), s: Session=Depends(db)):
 from . import chart
 return chart.patch(aid, x, ctx, s)

@router.post('/api/fiscal/periods/{pid}/closing-entry')
def fiscal_closing_entry(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 from . import closing
 return closing.close_entry(pid, ctx, s)

from app.schemas import JournalTemplateIn, TemplatePostIn
from . import templates as tpl

@router.get('/api/journal-templates')
def journal_templates(ctx=Depends(current), s: Session=Depends(db)):
 return tpl.tlist(ctx, s)

@router.post('/api/journal-templates')
def journal_template_add(x: JournalTemplateIn, ctx=Depends(current), s: Session=Depends(db)):
 return tpl.tadd(x, ctx, s)

@router.delete('/api/journal-templates/{tid}')
def journal_template_delete(tid: int, ctx=Depends(current), s: Session=Depends(db)):
 return tpl.tdelete(tid, ctx, s)

@router.post('/api/journal-templates/{tid}/post')
def journal_template_post(tid: int, x: TemplatePostIn, ctx=Depends(current), s: Session=Depends(db)):
 return tpl.tpost(tid, x, ctx, s)
