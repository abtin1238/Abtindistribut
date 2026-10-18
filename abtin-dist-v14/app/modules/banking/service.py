from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import D, audit, obj, same_company
from app.models import Account, BankAccount, Check, CheckHistory, Chequebook, JournalEntry, JournalLine, User
from app.services.accounting import CASH, OPEN_EQ, bank_balance, check_hist, entry_dict, post_entry
from app.services.banking import OPEN_CHECK, book_dict, get_account, leaf_for, refresh_book
import re
from .schemas import BankAccountIn, BankAccountPatch, ChequebookIn, ChequebookPatch, LeafVoidIn, BankTransferIn

def valid_iban(v:str)->bool:
 """شبا: IR + ۲۴ رقم و کنترل mod-97"""
 if not re.fullmatch(r'IR\d{24}',v): return False
 return int(''.join(str(int(ch,36)) for ch in v[4:]+v[:4]))%97==1

def _iban(v:Optional[str]):
 if v is None: return None
 v=re.sub(r'\s+','',v).upper()
 if v and not valid_iban(v): raise HTTPException(400,'شماره شبا نامعتبر است')
 return v

def _open_sum(s,cid,bid,kind):
 return D(s.scalar(select(func.coalesce(func.sum(Check.amount),0)).where(Check.company_id==cid,Check.bank_account_id==bid,Check.kind==kind,Check.status.in_(OPEN_CHECK))))

def acc_dict(s,cid,b):
 d=obj(b);bal=bank_balance(s,cid,b);oi=_open_sum(s,cid,b.id,'issued');orc=_open_sum(s,cid,b.id,'received')
 d.update({'balance':bal,'open_issued':oi,'open_received':orc,'projected':bal+orc-oi});return d

def accounts(ctx, s: Session):
 cid=ctx[1];return [acc_dict(s,cid,b) for b in s.scalars(select(BankAccount).where(BankAccount.company_id==cid).order_by(BankAccount.id))]

def add_account(x: BankAccountIn, ctx, s: Session):
 u,cid,r=ctx;name=x.name.strip();iban=_iban(x.iban)
 if not name: raise HTTPException(400,'نام حساب الزامی است')
 if s.scalar(select(BankAccount.id).where(BankAccount.company_id==cid,BankAccount.name==name)): raise HTTPException(409,'حسابی با این نام وجود دارد')
 b=BankAccount(company_id=cid,name=name,bank_name=x.bank_name.strip(),branch=x.branch.strip(),account_number=x.account_number.strip(),iban=iban,holder=x.holder.strip(),opening_balance=x.opening_balance);s.add(b);s.flush()
 code=f'1120{b.id:03d}'
 if s.scalar(select(Account.id).where(Account.company_id==cid,Account.code==code)): raise HTTPException(409,f'کد حساب {code} قبلاً در سرفصل‌ها استفاده شده است')
 b.ledger_code=code;s.add(Account(company_id=cid,code=code,name=f'بانک — {name}',type='asset'));s.flush()
 if D(x.opening_balance)>0: post_entry(s,cid,u.id,f'مانده اول دوره حساب بانکی {name}',[{'code':code,'debit':x.opening_balance},{'code':OPEN_EQ,'credit':x.opening_balance}],source=('bank_opening',b.id))
 audit(s,cid,u.id,'create','bank_account',b.id,x.model_dump());s.commit();s.refresh(b);return acc_dict(s,cid,b)

def edit_account(bid: int, x: BankAccountPatch, ctx, s: Session):
 u,cid,r=ctx;b=same_company(s,BankAccount,bid,cid);ch={k:v for k,v in x.model_dump(exclude_unset=True).items() if v is not None}
 if 'iban' in ch: ch['iban']=_iban(ch['iban'])
 if 'name' in ch:
  ch['name']=(ch['name'] or '').strip()
  if not ch['name']: raise HTTPException(400,'نام حساب الزامی است')
  if s.scalar(select(BankAccount.id).where(BankAccount.company_id==cid,BankAccount.name==ch['name'],BankAccount.id!=b.id)): raise HTTPException(409,'حسابی با این نام وجود دارد')
 if ch.get('active') is False and b.active:
  if bank_balance(s,cid,b)!=0: raise HTTPException(409,'حساب با مانده غیرصفر غیرفعال نمی‌شود')
  if _open_sum(s,cid,b.id,'issued')>0 or _open_sum(s,cid,b.id,'received')>0: raise HTTPException(409,'چک باز (در انتظار/ایداع‌شده) به این حساب وصل است')
 for k,v in ch.items(): setattr(b,k,v if not isinstance(v,str) else v.strip())
 if 'name' in ch:
  a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==b.ledger_code))
  if a: a.name=f'بانک — {b.name}'
 audit(s,cid,u.id,'update','bank_account',b.id,ch);s.commit();s.refresh(b);return acc_dict(s,cid,b)

def statement(bid: int, start: Optional[date], end: Optional[date], ctx, s: Session):
 cid=ctx[1];b=same_company(s,BankAccount,bid,cid)
 if start and end and start>end: raise HTTPException(400,'بازه‌ی تاریخ نامعتبر است')
 a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==b.ledger_code))
 rows=[];run=opening=Decimal(0)
 if a:
  q=select(JournalLine,JournalEntry).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,JournalLine.account_id==a.id).order_by(JournalEntry.id,JournalLine.id)
  for l,e in s.execute(q):
   dt=e.entry_date;run+=D(l.debit)-D(l.credit)
   if start and dt<start: opening=run;continue
   if end and dt>end: continue
   rows.append({'entry_id':e.id,'number':e.number,'date':e.entry_date,'description':e.description,'source_type':e.source_type,'debit':l.debit,'credit':l.credit,'balance':run})
 closing=rows[-1]['balance'] if rows else opening
 return {'account':{'id':b.id,'name':b.name,'ledger_code':b.ledger_code},'opening':opening,'rows':rows,'closing':closing}

def transfer(x: BankTransferIn, ctx, s: Session):
 """from/to خالی = صندوق. سند: بدهکار مقصد / بستانکار مبدأ؛ از حساب بانکی بیش از مانده برداشت نمی‌شود"""
 u,cid,r=ctx
 if x.from_account_id is None and x.to_account_id is None: raise HTTPException(400,'حداقل یکی از مبدأ یا مقصد باید حساب بانکی باشد')
 if x.from_account_id==x.to_account_id: raise HTTPException(400,'مبدأ و مقصد یکسان است')
 fb=get_account(s,cid,x.from_account_id) if x.from_account_id is not None else None
 tb=get_account(s,cid,x.to_account_id) if x.to_account_id is not None else None
 if fb and bank_balance(s,cid,fb)<D(x.amount): raise HTTPException(409,'موجودی حساب مبدأ کافی نیست')
 fc,tc=(fb.ledger_code if fb else CASH),(tb.ledger_code if tb else CASH)
 desc=f"انتقال وجه: {fb.name if fb else 'صندوق'} ← {tb.name if tb else 'صندوق'}"+(f' — {x.note.strip()}' if x.note.strip() else '')
 e=post_entry(s,cid,u.id,desc,[{'code':tc,'debit':x.amount},{'code':fc,'credit':x.amount}],source=('bank_transfer',None))
 audit(s,cid,u.id,'transfer','bank_account',None,x.model_dump());s.commit();return entry_dict(s,e)

def books(bank_account_id: Optional[int], ctx, s: Session):
 cid=ctx[1];q=select(Chequebook).where(Chequebook.company_id==cid)
 if bank_account_id: q=q.where(Chequebook.bank_account_id==bank_account_id)
 return [book_dict(s,c) for c in s.scalars(q.order_by(Chequebook.id.desc()).limit(500))]

def add_book(x: ChequebookIn, ctx, s: Session):
 u,cid,r=ctx;get_account(s,cid,x.bank_account_id)
 if x.end_no<x.start_no: raise HTTPException(400,'شمارهٔ پایان کوچک‌تر از شروع است')
 if x.end_no-x.start_no+1>500: raise HTTPException(400,'یک دسته‌چک حداکثر ۵۰۰ برگ دارد')
 series=x.series.strip()
 for o in s.scalars(select(Chequebook).where(Chequebook.company_id==cid,Chequebook.bank_account_id==x.bank_account_id,Chequebook.series==series,Chequebook.status!='cancelled')):
  if x.start_no<=o.end_no and o.start_no<=x.end_no: raise HTTPException(409,f'بازه با دسته‌چک #{o.id} ({o.start_no}–{o.end_no}) هم‌پوشانی دارد')
 c=Chequebook(company_id=cid,bank_account_id=x.bank_account_id,series=series,start_no=x.start_no,end_no=x.end_no);s.add(c);s.flush()
 audit(s,cid,u.id,'create','chequebook',c.id,x.model_dump());s.commit();s.refresh(c);return book_dict(s,c)

def set_book_status(bid: int, x: ChequebookPatch, ctx, s: Session):
 """active ↔ cancelled (دسته‌چک گم‌شده/مسدود)؛ «تمام‌شده» فقط خودکار با مصرف آخرین برگ"""
 u,cid,r=ctx;c=same_company(s,Chequebook,bid,cid)
 if x.status not in ('active','cancelled'): raise HTTPException(400,'وضعیت نامعتبر است (active یا cancelled)')
 if c.status=='finished': raise HTTPException(409,'دسته‌چک تمام‌شده قابل تغییر نیست')
 if x.status=='active' and c.status!='active':
  for o in s.scalars(select(Chequebook).where(Chequebook.company_id==cid,Chequebook.bank_account_id==c.bank_account_id,Chequebook.series==c.series,Chequebook.status!='cancelled',Chequebook.id!=c.id)):
   if c.start_no<=o.end_no and o.start_no<=c.end_no: raise HTTPException(409,f'بازه با دسته‌چک #{o.id} هم‌پوشانی دارد')
 c.status=x.status;audit(s,cid,u.id,'status','chequebook',c.id,{'status':x.status});s.commit();return book_dict(s,c)

def leaves(bid: int, ctx, s: Session):
 cid=ctx[1];c=same_company(s,Chequebook,bid,cid)
 byno={str(k.number).strip():k for k in s.scalars(select(Check).where(Check.chequebook_id==c.id))}
 rows=[]
 for n in range(c.start_no,c.end_no+1):
  k=byno.get(str(n))
  rows.append({'number':str(n),'state':'unused' if not k else 'void' if D(k.amount)==0 and k.status=='cancelled' else 'used','check_id':k.id if k else None,'status':k.status if k else None,'amount':k.amount if k else None,'due_date':k.due_date if k else None,'party':k.party if k else None})
 return {'book':book_dict(s,c),'leaves':rows}

def void_leaf(bid: int, x: LeafVoidIn, ctx, s: Session):
 """باطل‌کردن برگ سفید (خراب/گم‌شده)؛ برگ مصرف‌شده حساب می‌شود و سند مالی ندارد"""
 u,cid,r=ctx;c=s.get(Chequebook,bid,with_for_update=True)
 if not c or c.company_id!=cid: raise HTTPException(404,'دسته‌چک یافت نشد')
 if c.status!='active': raise HTTPException(409,'این دسته‌چک فعال نیست')
 n=leaf_for(s,c,x.number);ba=get_account(s,cid,c.bank_account_id,active=False)
 k=Check(company_id=cid,number=n,kind='issued',amount=0,due_date=date.today(),status='cancelled',bank=ba.bank_name,party='',notes=(x.note.strip() or 'برگ باطل‌شده'),bank_account_id=c.bank_account_id,chequebook_id=c.id);s.add(k);s.flush()
 refresh_book(s,c);check_hist(s,cid,u.id,k.id,'void_leaf','','cancelled',x.note);audit(s,cid,u.id,'void_leaf','chequebook',c.id,{'number':n});s.commit();return book_dict(s,c)

def checks_due(days: int, ctx, s: Session):
 """چک‌های باز (در انتظار/ایداع‌شده) با سررسید تا `days` روز دیگر + سررسیدگذشته‌ها؛ هشدار برای پیگیری"""
 cid=ctx[1];today=date.today();names={b.id:b.name for b in s.scalars(select(BankAccount).where(BankAccount.company_id==cid))}
 tot={'received':{'amount':Decimal(0),'count':0},'issued':{'amount':Decimal(0),'count':0}};rows=[]
 for c in s.scalars(select(Check).where(Check.company_id==cid,Check.status.in_(OPEN_CHECK),Check.due_date<=today+timedelta(days=days)).order_by(Check.due_date,Check.id).limit(500)):
  t=tot[c.kind];t['amount']+=D(c.amount);t['count']+=1
  rows.append({**obj(c),'days_left':(c.due_date-today).days,'overdue':c.due_date<today,'bank_account':names.get(c.bank_account_id,'')})
 return {'days':days,'today':today,'received':tot['received'],'issued':tot['issued'],'overdue_count':sum(1 for x in rows if x['overdue']),'rows':rows}

def check_history(chk: int, ctx, s: Session):
 cid=ctx[1];same_company(s,Check,chk,cid);out=[]
 for h in s.scalars(select(CheckHistory).where(CheckHistory.company_id==cid,CheckHistory.check_id==chk).order_by(CheckHistory.id)):
  u=s.get(User,h.user_id) if h.user_id else None;d=obj(h);d['user']=u.name if u else '';out.append(d)
 return out
