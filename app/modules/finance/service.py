from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import D, audit, list_page, obj, same_company
from app.core.config import utcnow
from app.core.security import has_perm
from app.models import FiscalPeriod, Account, Check, Chequebook, Customer, Invoice, JournalEntry, JournalLine, Order, Payment, Supplier
from app.services.accounting import BANK_FEE, bank_code, ACCOUNT_TYPES, AR, NR, AP, CHART, CHECK_FLOW, _jl_q, _range, acct, check_create_lines, entry_dict, party_balances, payment_lines, check_hist, post_check_status, post_entry, refresh_invoice_status, reverse_entry
from app.services.banking import bind_account, get_account, leaf_for, refresh_book
from .schemas import FiscalPeriodIn, PaymentIn, CheckIn, CheckStatusIn, CheckEndorseIn, JournalIn, AccountIn

def _cell(v):
 if isinstance(v,Decimal): return float(v)
 if isinstance(v,(date,datetime)): return v.isoformat()
 if isinstance(v,str) and v[:1] in ('=','+','-','@'): return "'"+v
 return v

def xlsx_response(name,headers,rows):
 import io;from openpyxl import Workbook
 wb=Workbook();ws=wb.active;ws.sheet_view.rightToLeft=True;ws.append(headers)
 for r in rows: ws.append([_cell(v) for v in r])
 b=io.BytesIO();wb.save(b);return Response(b.getvalue(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename={name}.xlsx','X-Content-Type-Options':'nosniff'})

def payment(x: PaymentIn, ctx, s: Session):
 u,cid,r=ctx
 if not has_perm(r,'finance.write') and (x.kind!='receipt' or x.supplier_id): raise HTTPException(403,'فقط دریافت از مشتری برای شما مجاز است')
 if not any([x.customer_id,x.supplier_id,x.invoice_id]): raise HTTPException(400,'طرف حساب یا فاکتور لازم است')
 if x.supplier_id and (x.customer_id or x.invoice_id): raise HTTPException(400,'پرداخت هم‌زمان به تأمین‌کننده و مشتری/فاکتور مجاز نیست')
 if x.bank_account_id:
  if x.method in ('cash','check'): raise HTTPException(400,'حساب بانکی فقط برای روش‌های بانکی (کارت/حواله/…) معتبر است')
  get_account(s,cid,x.bank_account_id)
 cust_id=x.customer_id
 if x.customer_id:
  c=s.get(Customer,x.customer_id)
  if not c or c.company_id!=cid:raise HTTPException(404,'مشتری یافت نشد')
 if x.supplier_id:
  sup=s.get(Supplier,x.supplier_id)
  if not sup or sup.company_id!=cid:raise HTTPException(404,'تأمین‌کننده یافت نشد')
 if x.invoice_id:
  inv=s.get(Invoice,x.invoice_id)
  if not inv or inv.company_id!=cid:raise HTTPException(404,'فاکتور یافت نشد')
  oc=s.get(Order,inv.order_id).customer_id
  if cust_id and cust_id!=oc: raise HTTPException(400,'فاکتور متعلق به این مشتری نیست')
  cust_id=oc
  if inv.status=='cancelled':raise HTTPException(409,'فاکتور باطل‌شده پرداخت نمی‌پذیرد')
  if x.kind=='refund':
   if x.amount>inv.paid:raise HTTPException(400,'مبلغ برگشت بیشتر از مبلغ پرداخت‌شده فاکتور است')
  elif x.amount>inv.total-inv.returned-inv.paid:raise HTTPException(400,'مبلغ پرداخت بیشتر از مانده فاکتور است')
 if cust_id and x.kind not in ('receipt','refund'):raise HTTPException(400,'نوع دریافت مشتری نامعتبر')
 d=x.model_dump();d['customer_id']=cust_id;p=Payment(company_id=cid,**d);s.add(p);s.flush()
 desc,L=payment_lines(s,p);post_entry(s,cid,u.id,desc,L,source=('payment',p.id))
 if x.invoice_id:
  inv=s.get(Invoice,x.invoice_id);inv.paid+=(-x.amount if x.kind=='refund' else x.amount);refresh_invoice_status(inv)
 audit(s,cid,u.id,'payment','payment',p.id,x.model_dump());s.commit();s.refresh(p);return obj(p)

def payments(response: Response, limit: int, offset: int, ctx, s: Session):
 return [obj(x) for x in list_page(s, Payment, ctx[1], response, limit, offset)]

def checks(response: Response, limit: int, offset: int, ctx, s: Session):
 return [obj(x) for x in list_page(s, Check, ctx[1], response, limit, offset)]

def add_check(x: CheckIn, ctx, s: Session):
 u,cid,r=ctx
 if x.kind not in ('received','issued'): raise HTTPException(400,'نوع چک نامعتبر است')
 if x.customer_id:
  c=s.get(Customer,x.customer_id)
  if x.kind!='received' or not c or c.company_id!=cid: raise HTTPException(400,'مشتری نامعتبر برای چک')
 if x.supplier_id:
  sp=s.get(Supplier,x.supplier_id)
  if x.kind!='issued' or not sp or sp.company_id!=cid: raise HTTPException(400,'تأمین‌کننده نامعتبر برای چک')
 d=x.model_dump();d['number']=d['number'].strip();cb=None
 if x.kind=='received' and (x.bank_account_id or x.chequebook_id): raise HTTPException(400,'حساب بانکی چک دریافتی هنگام ایداع/وصول تعیین می‌شود')
 if x.chequebook_id:
  cb=s.get(Chequebook,x.chequebook_id,with_for_update=True)
  if not cb or cb.company_id!=cid: raise HTTPException(404,'دسته‌چک یافت نشد')
  if cb.status!='active': raise HTTPException(409,'این دسته‌چک فعال نیست')
  if x.bank_account_id and x.bank_account_id!=cb.bank_account_id: raise HTTPException(400,'دسته‌چک متعلق به حساب بانکی دیگری است')
  d['number']=leaf_for(s,cb,d['number']);d['bank_account_id']=cb.bank_account_id
 elif not d['number']: raise HTTPException(400,'شماره چک الزامی است')
 if d.get('bank_account_id'):
  b=get_account(s,cid,d['bank_account_id'])
  if not d['bank']: d['bank']=b.bank_name
 q=Check(company_id=cid,**d);s.add(q);s.flush()
 if cb: refresh_book(s,cb)
 post_entry(s,cid,u.id,f'ثبت چک {q.number}',check_create_lines(q),source=('check_created',q.id));check_hist(s,cid,u.id,q.id,'created','',q.status,f'{q.kind} / {q.amount}')
 audit(s,cid,u.id,'create','check',q.id);s.commit();s.refresh(q);return obj(q)

def update_check(cid: int, x: CheckStatusIn, ctx, s: Session):
 u,cid0,r=ctx;q=s.get(Check,cid,with_for_update=True)
 if not q or q.company_id!=cid0:raise HTTPException(404,'چک یافت نشد')
 if x.status not in CHECK_FLOW:raise HTTPException(400,'وضعیت چک نامعتبر')
 if x.status=='endorsed': raise HTTPException(400,'برای خرج چک از endpoint «/endorse» با تعیین تأمین‌کننده استفاده کنید')
 if x.status==q.status: return obj(q)
 if x.status not in CHECK_FLOW[q.status]: raise HTTPException(409,f'انتقال وضعیت چک از {q.status} به {x.status} مجاز نیست')
 if x.bank_account_id is not None and q.kind=='received' and x.status not in ('deposited','cleared'): raise HTTPException(400,'حساب بانکی چک دریافتی فقط هنگام ایداع یا وصول تعیین می‌شود')
 frm=q.status;bind_account(s,cid0,q,x.bank_account_id)
 if x.fee>0 and x.status!='bounced': raise HTTPException(400,'کارمزد فقط هنگام برگشت چک قابل ثبت است')
 post_check_status(s,cid0,u.id,q,x.status);q.status=x.status;check_hist(s,cid0,u.id,q.id,'status',frm,x.status,(x.note+(f' | کارمزد برگشت {x.fee}' if x.fee>0 else ''))[:300])
 if x.fee>0: post_entry(s,cid0,u.id,f'کارمزد برگشت چک {q.number}',[{'code':BANK_FEE,'debit':x.fee},{'code':bank_code(s,q.bank_account_id),'credit':x.fee}],source=('check_bounce_fee',q.id))
 audit(s,cid0,u.id,'status','check',q.id,{'status':x.status,'bank_account_id':q.bank_account_id});s.commit();return obj(q)

def journal(x: JournalIn, ctx, s: Session):
 u,cid,r=ctx;L=[]
 for l in x.lines:
  if (l.debit>0)==(l.credit>0): raise HTTPException(400,'هر سطر باید دقیقاً یکی از بدهکار یا بستانکار را داشته باشد')
  if l.customer_id and not s.scalar(select(Customer.id).where(Customer.id==l.customer_id,Customer.company_id==cid)): raise HTTPException(404,'مشتری یافت نشد')
  if l.supplier_id and not s.scalar(select(Supplier.id).where(Supplier.id==l.supplier_id,Supplier.company_id==cid)): raise HTTPException(404,'تأمین‌کننده یافت نشد')
  L.append({'code':l.account_code,'debit':l.debit,'credit':l.credit,'customer_id':l.customer_id,'supplier_id':l.supplier_id,'memo':l.memo})
 e=post_entry(s,cid,u.id,x.description,L,source=('manual',None),entry_date=x.entry_date);audit(s,cid,u.id,'post','journal',e.id,x.model_dump());s.commit();return entry_dict(s,e)

def journal_list(ctx, s: Session):
 es=s.scalars(select(JournalEntry).where(JournalEntry.company_id==ctx[1]).order_by(JournalEntry.id.desc()).limit(500)).all();return [entry_dict(s,e) for e in es]

def journal_get(eid: int, ctx, s: Session):
 return entry_dict(s, same_company(s, JournalEntry, eid, ctx[1]))

def journal_reverse(eid: int, reason: str, ctx, s: Session):
 u,cid,r=ctx;e=same_company(s,JournalEntry,eid,cid)
 if e.source_type not in (None,'manual'): raise HTTPException(409,'سند خودکار فقط از طریق عملیات مبدأ (لغو/برگشت) قابل اصلاح است')
 rv=reverse_entry(s,cid,u.id,e,reason);audit(s,cid,u.id,'reverse','journal',e.id,{'reversal':rv.number});s.commit();return entry_dict(s,rv)

def accounts_list(ctx, s: Session):
 for c in CHART: acct(s,ctx[1],c)
 s.commit();return [obj(x) for x in s.scalars(select(Account).where(Account.company_id==ctx[1]).order_by(Account.code))]

def account_add(x: AccountIn, ctx, s: Session):
 from .chart import add
 return add(x, ctx, s)

def trial_balance(ctx, s: Session):
 q=select(Account.code,Account.name,Account.type,func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).select_from(Account).outerjoin(JournalLine,JournalLine.account_id==Account.id).where(Account.company_id==ctx[1],Account.level>=3).group_by(Account.id,Account.code,Account.name,Account.type).order_by(Account.code)
 rows=[{'code':c,'name':n,'type':t_,'debit':D(d),'credit':D(cr),'balance':D(d)-D(cr)} for c,n,t_,d,cr in s.execute(q)]
 td=sum((x['debit'] for x in rows),Decimal(0));tc=sum((x['credit'] for x in rows),Decimal(0));return {'rows':rows,'total_debit':td,'total_credit':tc,'balanced':td==tc}

def profit_loss_monthly(months: int, ctx, s: Session):
 """روند ماهانه‌ی درآمد/هزینه بر اساس ماه شمسی (از اسناد ثبت‌شده)؛ مجوز finance.read از پیشوند مسیر"""
 from datetime import timedelta
 from app.services.jalali import MONTHS,to_jalali
 today=date.today();jy,jm,_=to_jalali(today);keys=[]
 for _i in range(months):keys.append((jy,jm));jm-=1;jy,jm=(jy-1,12) if jm==0 else (jy,jm)
 keys.reverse();agg={k:{'revenue':Decimal(0),'expense':Decimal(0)} for k in keys}
 q=select(JournalEntry.entry_date,Account.type,JournalLine.debit,JournalLine.credit).select_from(JournalLine).join(Account,Account.id==JournalLine.account_id).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==ctx[1],Account.type.in_(['revenue','expense']),JournalEntry.created_at>=today-timedelta(days=months*31+31))
 for at,ty,d_,c_ in s.execute(q):
  k=to_jalali(at)[:2]
  if k in agg:agg[k][ty]+=(D(c_)-D(d_)) if ty=='revenue' else (D(d_)-D(c_))
 return {'months':[{'year':k[0],'month':k[1],'label':MONTHS[k[1]-1],'revenue':v['revenue'],'expense':v['expense']} for k,v in agg.items()]}

def customer_ledger(customer_id: int, ctx, s: Session):
 cid=ctx[1];c=same_company(s,Customer,customer_id,cid);run=Decimal(0);rows=[]
 q=select(JournalLine,JournalEntry).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).join(Account,Account.id==JournalLine.account_id).where(JournalLine.company_id==cid,JournalLine.customer_id==customer_id,Account.code==AR).order_by(JournalEntry.id,JournalLine.id)
 for l,e in s.execute(q):
  run+=D(l.debit)-D(l.credit);rows.append({'entry_id':e.id,'number':e.number,'date':e.entry_date,'description':e.description,'source_type':e.source_type,'debit':l.debit,'credit':l.credit,'balance':run})
 return {'customer':{'id':c.id,'name':c.name,'code':c.code},'balance':run,'rows':rows}

def profit_loss(start: Optional[date], end: Optional[date], ctx, s: Session):
 _range(start,end);rows=[]
 for c,n,ty,d,cr in s.execute(_jl_q(ctx[1],['revenue','expense'],start,end)): rows.append({'code':c,'name':n,'type':ty,'amount':D(cr)-D(d) if ty=='revenue' else D(d)-D(cr)})
 rev=sum((x['amount'] for x in rows if x['type']=='revenue'),Decimal(0));exp=sum((x['amount'] for x in rows if x['type']=='expense'),Decimal(0))
 cogs=sum((x['amount'] for x in rows if x['code']=='5100'),Decimal(0))
 return {'start':start,'end':end,'rows':rows,'revenue':rev,'expense':exp,'cogs':cogs,'gross_profit':rev-cogs,'net_profit':rev-exp}

def balance_sheet(end: Optional[date], ctx, s: Session):
 rows=[]
 for c,n,ty,d,cr in s.execute(_jl_q(ctx[1],['asset','liability','equity'],None,end,closing=True)): rows.append({'code':c,'name':n,'type':ty,'amount':D(d)-D(cr) if ty=='asset' else D(cr)-D(d)})
 earn=Decimal(0)
 for c,n,ty,d,cr in s.execute(_jl_q(ctx[1],['revenue','expense'],None,end,closing=True)): earn+=(D(cr)-D(d)) if ty=='revenue' else -(D(d)-D(cr))
 tot=lambda k: sum((x['amount'] for x in rows if x['type']==k),Decimal(0))
 a,l,e=tot('asset'),tot('liability'),tot('equity')
 return {'end':end,'rows':rows,'assets':a,'liabilities':l,'equity':e,'current_earnings':earn,'balanced':a==l+e+earn}

def general_ledger(account_code: str, start: Optional[date], end: Optional[date], ctx, s: Session):
 _range(start,end);cid=ctx[1];a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==account_code))
 if not a: raise HTTPException(404,'حساب یافت نشد')
 base=select(JournalLine,JournalEntry).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,JournalLine.account_id==a.id)
 run=Decimal(0)
 if start:
  o=s.execute(select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,JournalLine.account_id==a.id,func.date(JournalEntry.created_at)<start)).one();run=D(o[0])-D(o[1])
 opening=run;q=base
 if start: q=q.where(JournalEntry.entry_date>=start)
 if end: q=q.where(JournalEntry.entry_date<=end)
 rows=[]
 for l,e in s.execute(q.order_by(JournalEntry.id,JournalLine.id)):
  run+=D(l.debit)-D(l.credit);rows.append({'entry_id':e.id,'number':e.number,'date':e.entry_date,'description':e.description,'debit':l.debit,'credit':l.credit,'balance':run})
 return {'account':{'code':a.code,'name':a.name,'type':a.type},'opening':opening,'rows':rows,'closing':run}

def aging(as_of: Optional[date], ctx, s: Session):
 cid=ctx[1];ref=as_of or date.today();out={};names={c.id:c for c in s.scalars(select(Customer).where(Customer.company_id==cid))}
 for inv,cust in s.execute(select(Invoice,Order.customer_id).join(Order,Order.id==Invoice.order_id).where(Invoice.company_id==cid,Invoice.status.in_(['open','partial']))):
  amt=D(inv.total)-D(inv.returned)-D(inv.paid)
  if amt<=0: continue
  days=max(0,(ref-inv.issued_at.date()).days);k='b0_30' if days<=30 else 'b31_60' if days<=60 else 'b61_90' if days<=90 else 'b90p'
  r=out.setdefault(cust,{'b0_30':Decimal(0),'b31_60':Decimal(0),'b61_90':Decimal(0),'b90p':Decimal(0)});r[k]+=amt
 led=party_balances(s,cid,'customer');rows=[]
 for cust in set(out)|{k for k,v in led.items() if v!=0}:
  b=out.get(cust,{'b0_30':Decimal(0),'b31_60':Decimal(0),'b61_90':Decimal(0),'b90p':Decimal(0)});inv_total=sum(b.values(),Decimal(0));c=names.get(cust)
  rows.append({'customer_id':cust,'customer':c.name if c else '','code':c.code if c else '',**b,'invoices_total':inv_total,'ledger_balance':led.get(cust,Decimal(0)),'unallocated':led.get(cust,Decimal(0))-inv_total})
 rows.sort(key=lambda x:x['customer'])
 tot={k:sum((x[k] for x in rows),Decimal(0)) for k in ('b0_30','b31_60','b61_90','b90p','invoices_total','ledger_balance','unallocated')}
 return {'as_of':ref,'rows':rows,'totals':tot}

def trial_balance_xlsx(ctx, s: Session):
 d=trial_balance(ctx,s);return xlsx_response('trial-balance',['کد','حساب','نوع','بدهکار','بستانکار','مانده'],[[x['code'],x['name'],x['type'],x['debit'],x['credit'],x['balance']] for x in d['rows']])

def aging_xlsx(as_of: Optional[date], ctx, s: Session):
 d=aging(as_of,ctx,s);return xlsx_response('aging',['کد','مشتری','۰-۳۰','۳۱-۶۰','۶۱-۹۰','بیش از ۹۰','جمع فاکتورها','مانده‌ی دفتر','علی‌الحساب/تفاوت'],[[x['code'],x['customer'],x['b0_30'],x['b31_60'],x['b61_90'],x['b90p'],x['invoices_total'],x['ledger_balance'],x['unallocated']] for x in d['rows']])

def profit_loss_xlsx(start: Optional[date], end: Optional[date], ctx, s: Session):
 d=profit_loss(start,end,ctx,s);return xlsx_response('profit-loss',['کد','حساب','نوع','مبلغ'],[[x['code'],x['name'],x['type'],x['amount']] for x in d['rows']]+[['','سود خالص','',d['net_profit']]])

def general_ledger_xlsx(account_code: str, start: Optional[date], end: Optional[date], ctx, s: Session):
 d=general_ledger(account_code,start,end,ctx,s);return xlsx_response('general-ledger-'+''.join(ch for ch in account_code if ch.isalnum()),['شماره سند','تاریخ','شرح','بدهکار','بستانکار','مانده'],[[x['number'],x['date'],x['description'],x['debit'],x['credit'],x['balance']] for x in d['rows']])

def fiscal_list(ctx, s: Session):
 return [obj(p) for p in s.scalars(select(FiscalPeriod).where(FiscalPeriod.company_id==ctx[1]).order_by(FiscalPeriod.start_date.desc())).all()]

def fiscal_create(x: FiscalPeriodIn, ctx, s: Session):
 u,cid,r=ctx
 if not x.name.strip(): raise HTTPException(400,'نام دوره الزامی است')
 if x.end_date<x.start_date: raise HTTPException(400,'پایان دوره قبل از شروع آن است')
 if s.scalar(select(FiscalPeriod.id).where(FiscalPeriod.company_id==cid,FiscalPeriod.start_date<=x.end_date,FiscalPeriod.end_date>=x.start_date)): raise HTTPException(409,'این بازه با یک دورهٔ دیگر هم‌پوشانی دارد')
 p=FiscalPeriod(company_id=cid,name=x.name.strip(),start_date=x.start_date,end_date=x.end_date);s.add(p);s.flush();audit(s,cid,u.id,'create','fiscal_period',p.id,x.model_dump());s.commit();return obj(p)

def fiscal_close(pid: int, ctx, s: Session):
 u,cid,r=ctx;p=same_company(s,FiscalPeriod,pid,cid)
 if p.closed: raise HTTPException(409,'دوره قبلاً بسته شده است')
 p.closed=True;p.closed_by=u.id;p.closed_at=utcnow();audit(s,cid,u.id,'close','fiscal_period',p.id,{});s.commit();return obj(p)

def fiscal_reopen(pid: int, ctx, s: Session):
 u,cid,r=ctx;p=same_company(s,FiscalPeriod,pid,cid)
 if not p.closed: raise HTTPException(409,'دوره باز است')
 p.closed=False;p.closed_by=None;p.closed_at=None;audit(s,cid,u.id,'reopen','fiscal_period',p.id,{});s.commit();return obj(p)

def endorse_check(chk: int, x: CheckEndorseIn, ctx, s: Session):
 """خرج چک دریافتی به تأمین‌کننده: بدهی تأمین‌کننده کم و اسناد دریافتنی بسته می‌شود"""
 u,cid,r=ctx;q=s.get(Check,chk,with_for_update=True)
 if not q or q.company_id!=cid: raise HTTPException(404,'چک یافت نشد')
 if q.kind!='received': raise HTTPException(400,'فقط چک دریافتی قابل خرج‌کردن است')
 if q.status!='pending': raise HTTPException(409,'فقط چک در وضعیت «pending» قابل خرج‌کردن است')
 sp=s.get(Supplier,x.supplier_id)
 if not sp or sp.company_id!=cid: raise HTTPException(404,'تأمین‌کننده یافت نشد')
 post_entry(s,cid,u.id,f'خرج چک {q.number} به {sp.name}',[{'code':AP,'debit':q.amount,'supplier_id':sp.id},{'code':NR,'credit':q.amount}],source=('check_endorsed',q.id))
 frm=q.status;q.status='endorsed';q.endorsed_supplier_id=sp.id;q.endorsed_at=utcnow();check_hist(s,cid,u.id,q.id,'endorse',frm,'endorsed',f'به {sp.name}');audit(s,cid,u.id,'endorse','check',q.id,{'supplier_id':sp.id});s.commit();return obj(q)
