from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy import select
from app.models import BankAccount,Check

OPEN_CHECK=('pending','deposited')
def book_leaves(cb): return cb.end_no-cb.start_no+1
def used_numbers(s,cb):
 """شماره‌ی برگ‌های مصرف‌شده‌ی دسته‌چک (چک ثبت‌شده یا برگ باطل‌شده)"""
 return {str(n).strip() for n in s.scalars(select(Check.number).where(Check.chequebook_id==cb.id))}
def leaf_for(s,cb,number):
 """شماره‌ی برگ را اعتبارسنجی می‌کند؛ خالی = اولین برگ مصرف‌نشده"""
 used=used_numbers(s,cb);number=(number or '').strip()
 if not number:
  for n in range(cb.start_no,cb.end_no+1):
   if str(n) not in used: return str(n)
  raise HTTPException(409,'همه‌ی برگ‌های این دسته‌چک مصرف شده است')
 if not number.isdigit() or not (cb.start_no<=int(number)<=cb.end_no): raise HTTPException(400,f'شماره‌ی برگ باید عددی بین {cb.start_no} و {cb.end_no} باشد')
 number=str(int(number))
 if number in used: raise HTTPException(409,'این برگ قبلاً مصرف شده است')
 return number
def refresh_book(s,cb):
 """با مصرف آخرین برگ، دسته‌چک خودکار «تمام‌شده» می‌شود"""
 if cb.status=='active' and len(used_numbers(s,cb))>=book_leaves(cb): cb.status='finished'
def book_dict(s,cb):
 used=used_numbers(s,cb);nxt=next((n for n in range(cb.start_no,cb.end_no+1) if str(n) not in used),None)
 ba=s.get(BankAccount,cb.bank_account_id)
 return {'id':cb.id,'bank_account_id':cb.bank_account_id,'bank_account':ba.name if ba else '','series':cb.series,'start_no':cb.start_no,'end_no':cb.end_no,'status':cb.status,'total':book_leaves(cb),'used':len(used),'remaining':book_leaves(cb)-len(used),'next_no':nxt,'created_at':cb.created_at}
def get_account(s,cid,bid,active=True):
 b=s.get(BankAccount,bid)
 if not b or b.company_id!=cid: raise HTTPException(404,'حساب بانکی یافت نشد')
 if active and not b.active: raise HTTPException(409,'حساب بانکی غیرفعال است')
 return b
def bind_account(s,cid,chk,bid):
 """حساب بانکی را به چک وصل می‌کند؛ چکی که قبلاً به حسابی وصل شده با حساب دیگر قابل‌جابه‌جایی نیست"""
 if bid is None: return
 b=get_account(s,cid,bid)
 if chk.bank_account_id and chk.bank_account_id!=b.id: raise HTTPException(409,'این چک قبلاً به حساب بانکی دیگری وصل شده است')
 chk.bank_account_id=b.id
 if not chk.bank: chk.bank=b.bank_name
