from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import or_, func,select
from sqlalchemy.exc import IntegrityError
from app.core.common import D,Q2,num,obj
from app.services.costing import C4,split_return_discount,weighted_avg,weighted_avg_out
from app.core.config import utcnow
from app.core.database import SessionLocal
from app.models import Account,BankAccount,Campaign,Check,CheckHistory,Invoice,InvoiceLine,JournalEntry,JournalLine,Order,Payment,PriceRule,Product,Purchase,SalesReturn,SalesReturnLine,Sequence,Setting,Stock,StockMove

AR,AP,CASH,BANK,NR,NP,INVT,VAT,SALES,FREIGHT='1210','2110','1110','1120','1130','2120','1310','2210','4110','4120'
SDISC,COGS,INV_ADJ='4130','5100','5200'
SAL_EXP,SAL_PAY='5300','2310'
BANK_FEE,BANK_INT='5400','4210'
RETAINED='3200'
OPEN_EQ='3100'
CHART={CASH:('صندوق','asset'),BANK:('بانک','asset'),NR:('اسناد دریافتنی (چک‌های دریافتی)','asset'),AR:('حساب‌های دریافتنی مشتریان','asset'),INVT:('موجودی کالا','asset'),AP:('حساب‌های پرداختنی تأمین‌کنندگان','liability'),NP:('اسناد پرداختنی (چک‌های پرداختی)','liability'),VAT:('مالیات بر ارزش افزوده','liability'),SALES:('درآمد فروش','revenue'),FREIGHT:('درآمد حمل','revenue'),OPEN_EQ:('مانده اول دوره / تعدیل ورود اطلاعات','equity'),SDISC:('تخفیفات فروش','revenue'),COGS:('بهای تمام‌شده‌ی کالای فروش‌رفته','expense'),INV_ADJ:('اضافه/کسری و تعدیل موجودی','expense'),SAL_EXP:('هزینه حقوق و دستمزد','expense'),SAL_PAY:('حقوق پرداختنی','liability'),BANK_FEE:('کارمزد و هزینه‌های بانکی','expense'),BANK_INT:('سود سپرده بانکی','revenue'),RETAINED:('سود (زیان) انباشته','equity')}
ACCOUNT_TYPES={'asset','liability','equity','revenue','expense'}
def acct(s,cid,code):
 a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==code))
 if a:
  if (a.level or 3)<3: raise HTTPException(400,f'حساب «{a.name}» ({code}) گروه/کل است؛ ثبت سند فقط روی معین یا تفصیلی مجاز است')
  if not a.active: raise HTTPException(400,f'حساب «{a.name}» ({code}) غیرفعال است')
  return a
 if code not in CHART: raise HTTPException(400,f'حساب {code} تعریف نشده است')
 try:
  with s.begin_nested(): a=Account(company_id=cid,code=code,name=CHART[code][0],type=CHART[code][1]);s.add(a);s.flush()
 except IntegrityError: a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==code))
 return a
def cash_code(method): return CASH if method=='cash' else NR if method=='check' else BANK
def bank_code(s,bank_account_id):
 """حساب معینِ بانکِ مشخص؛ بدون حساب (داده‌ی قدیمی) همان «بانک» عمومی 1120"""
 if bank_account_id:
  b=s.get(BankAccount,bank_account_id)
  if b and b.ledger_code: return b.ledger_code
 return BANK
def bank_codes(s,cid):
 """کد 1120 عمومی + حساب معینِ همه‌ی حساب‌های بانکی شرکت (برای جمع «بانک» در داشبورد و گزارش مالی)"""
 return [BANK]+[c for c in s.scalars(select(BankAccount.ledger_code).where(BankAccount.company_id==cid)) if c]
def bank_balance(s,cid,b):
 """مانده‌ی حساب بانکی از دفتر کل (بدهکار − بستانکار حساب معین اختصاصی)"""
 a=s.scalar(select(Account).where(Account.company_id==cid,Account.code==b.ledger_code))
 if not a: return Decimal(0)
 d,c=s.execute(select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).where(JournalLine.company_id==cid,JournalLine.account_id==a.id)).one()
 return D(d)-D(c)
def check_hist(s,cid,uid,check_id,action,frm='',to='',note=''): s.add(CheckHistory(company_id=cid,check_id=check_id,user_id=uid,action=action,from_status=frm,to_status=to,note=note[:300]))
def assert_period_open(s,cid,on=None):
 """قفل دورهٔ مالی: ثبت سند در تاریخی که داخل دورهٔ بسته است مجاز نیست"""
 from app.models import FiscalPeriod
 d=on or utcnow().date()
 p=s.scalar(select(FiscalPeriod).where(FiscalPeriod.company_id==cid,FiscalPeriod.closed==True,FiscalPeriod.start_date<=d,FiscalPeriod.end_date>=d))
 if p: raise HTTPException(409,f'دورهٔ مالی «{p.name}» بسته است؛ ثبت یا معکوس‌کردن سند در این تاریخ مجاز نیست')
def post_entry(s,cid,uid,desc,lines,source=None,reverses=None,entry_date=None):
 """entry_date: تاریخ سند (پیش‌فرض امروز؛ آینده مجاز نیست)؛ قفل دوره‌ی مالی بر اساس همین تاریخ بررسی می‌شود"""
 ed=entry_date or utcnow().date()
 if ed>utcnow().date(): raise HTTPException(400,'تاریخ سند نمی‌تواند در آینده باشد')
 assert_period_open(s,cid,ed)
 ls=[];td=tc=Decimal(0)
 for l in lines:
  d=D(l.get('debit')).quantize(Q2);c=D(l.get('credit')).quantize(Q2)
  if d<0 or c<0 or (d>0 and c>0): raise HTTPException(400,'سطر سند نامعتبر است')
  if d==0 and c==0: continue
  ls.append((l,d,c));td+=d;tc+=c
 if td!=tc or td<=0: raise HTTPException(400,'سند باید متوازن باشد (جمع بدهکار = جمع بستانکار) و مبلغ مثبت داشته باشد')
 e=JournalEntry(company_id=cid,number=num('JE',JournalEntry,s),description=desc,debit=td,credit=tc,status='posted',entry_date=ed,source_type=source[0] if source else None,source_id=source[1] if source else None,reverses_id=reverses,created_by=uid);s.add(e);s.flush()
 for l,d,c in ls: s.add(JournalLine(entry_id=e.id,company_id=cid,account_id=acct(s,cid,l['code']).id,debit=d,credit=c,customer_id=l.get('customer_id'),supplier_id=l.get('supplier_id'),memo=l.get('memo','')))
 s.flush();return e
def reverse_entry(s,cid,uid,e,reason=''):
 if e.status=='reversed' or e.reverses_id: raise HTTPException(409,'این سند قبلاً معکوس شده یا خودش سند معکوس است')
 ls=s.scalars(select(JournalLine).where(JournalLine.entry_id==e.id)).all()
 r=post_entry(s,cid,uid,f'معکوس سند {e.number}'+(f' — {reason}' if reason else ''),[{'code':s.get(Account,l.account_id).code,'debit':l.credit,'credit':l.debit,'customer_id':l.customer_id,'supplier_id':l.supplier_id,'memo':l.memo} for l in ls],source=('reversal',e.id),reverses=e.id)
 e.status='reversed';return r
def source_entry(s,cid,stype,sid): return s.scalar(select(JournalEntry).where(JournalEntry.company_id==cid,JournalEntry.source_type==stype,JournalEntry.source_id==sid,JournalEntry.reverses_id==None))
def party_balances(s,cid,kind,pid=None):
 col=JournalLine.customer_id if kind=='customer' else JournalLine.supplier_id;code=AR if kind=='customer' else AP
 q=select(col,func.sum(JournalLine.debit),func.sum(JournalLine.credit)).join(Account,Account.id==JournalLine.account_id).where(JournalLine.company_id==cid,Account.code==code,col.is_not(None)).group_by(col)
 if pid is not None: q=q.where(col==pid)
 return {k:(D(d)-D(c) if kind=='customer' else D(c)-D(d)) for k,d,c in s.execute(q)}
def party_balance(s,cid,kind,pid): return party_balances(s,cid,kind,pid).get(pid,Decimal(0))
def payment_lines(s,p):
 cash=cash_code(p.method);a=D(p.amount)
 if cash==BANK: cash=bank_code(s,getattr(p,'bank_account_id',None))
 if p.customer_id:
  if p.kind=='receipt': return f'دریافت از مشتری #{p.id}',[{'code':cash,'debit':a},{'code':AR,'credit':a,'customer_id':p.customer_id}]
  return f'برگشت وجه به مشتری #{p.id}',[{'code':AR,'debit':a,'customer_id':p.customer_id},{'code':cash,'credit':a}]
 if p.kind=='payment': return f'پرداخت به تأمین‌کننده #{p.id}',[{'code':AP,'debit':a,'supplier_id':p.supplier_id},{'code':cash,'credit':a}]
 return f'دریافت از تأمین‌کننده #{p.id}',[{'code':cash,'debit':a},{'code':AP,'credit':a,'supplier_id':p.supplier_id}]
def invoice_lines(inv,customer_id,discount=0):
 """درآمد به‌صورت ناخالص (subtotal+تخفیف) و تخفیف جدا در 4130 بدهکار می‌شود؛ جمع بدهکار = جمع بستانکار."""
 d=D(discount)
 return [{'code':AR,'debit':inv.total,'customer_id':customer_id},{'code':SDISC,'debit':d},{'code':SALES,'credit':D(inv.subtotal)+d},{'code':VAT,'credit':inv.tax},{'code':FREIGHT,'credit':inv.shipping}]
def purchase_lines(p): return [{'code':INVT,'debit':p.total},{'code':AP,'credit':p.total,'supplier_id':p.supplier_id}]
def check_create_lines(c):
 a=D(c.amount)
 if c.kind=='received': return [{'code':NR,'debit':a},{'code':AR,'credit':a,'customer_id':c.customer_id}]
 return [{'code':AP,'debit':a,'supplier_id':c.supplier_id},{'code':NP,'credit':a}]
CHECK_FLOW={'pending':{'deposited','cleared','bounced','cancelled','returned','endorsed'},'endorsed':set(),'deposited':{'cleared','bounced'},'cleared':set(),'bounced':set(),'cancelled':set(),'returned':set()}
def post_check_status(s,cid,uid,c,new):
 a=D(c.amount);bk=bank_code(s,getattr(c,'bank_account_id',None))
 if c.kind=='received':
  L=[{'code':bk,'debit':a},{'code':NR,'credit':a}] if new=='cleared' else [{'code':AR,'debit':a,'customer_id':c.customer_id},{'code':NR,'credit':a}] if new in ('bounced','cancelled','returned') else None
 else:
  L=[{'code':NP,'debit':a},{'code':bk,'credit':a}] if new=='cleared' else [{'code':NP,'debit':a},{'code':AP,'credit':a,'supplier_id':c.supplier_id}] if new in ('bounced','cancelled','returned') else None
 if new=='endorsed': return  # سند خرج چک در endpoint مخصوص (با تأمین‌کننده) ثبت می‌شود
 if L: post_entry(s,cid,uid,f'چک {c.number} ← {new}',L,source=('check_'+new,c.id))
def refresh_invoice_status(inv):
 if inv.status=='cancelled': return
 eff=D(inv.total)-D(inv.returned);paid=D(inv.paid)
 set_invoice_status(inv,'paid' if paid>=eff else 'open' if paid<=0 else 'partial')
def on_hand(s,pid): return D(s.scalar(select(func.coalesce(func.sum(Stock.quantity),0)).where(Stock.product_id==pid)))
def apply_receipt_cost(s,p,qty,unit_cost):
 """میانگین موزون را به‌روز می‌کند؛ باید «قبل از» افزودن qty به Stock و با قفل ردیف کالا صدا زده شود."""
 p.avg_cost=weighted_avg(on_hand(s,p.id),p.avg_cost,qty,unit_cost);return p.avg_cost
def apply_return_cost(s,p,qty,unit_cost):
 """میانگین موزون را پس از برگشت از خرید بازمحاسبه می‌کند؛ باید «قبل از» کم‌کردن qty از Stock و با قفل ردیف کالا صدا زده شود."""
 p.avg_cost=weighted_avg_out(on_hand(s,p.id),p.avg_cost,qty,unit_cost);return p.avg_cost
def post_cogs(s,cid,uid,inv,issued):
 """بهای تمام‌شده‌ی اقلام خارج‌شده از انبار با میانگین لحظه‌ی خروج؛ روی سطر فاکتور ثبت و سند COGS ساخته می‌شود."""
 lines={l.product_id:l for l in s.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id==inv.id))} if inv else {};total=Decimal(0)
 for pid,q in issued:
  q=D(q)
  if q<=0: continue
  p=s.get(Product,pid,with_for_update=True);unit=D(p.avg_cost);amt=(q*unit).quantize(Q2);l=lines.get(pid)
  if l: l.unit_cost=unit;l.cogs=D(l.cogs)+amt
  total+=amt
 if inv and total>0: post_entry(s,inv.company_id,uid,f'بهای تمام‌شده‌ی فاکتور {inv.number}',[{'code':COGS,'debit':total},{'code':INVT,'credit':total}],source=('cogs',inv.id))
 return total
def post_stock_adjust(s,cid,uid,p,delta,ref,opening=False):
 """تعدیل دستی/ورود اطلاعات با بهای میانگین فعلی؛ اگر بها هنوز نامشخص (۰) باشد سندی ساخته نمی‌شود."""
 delta=D(delta)
 if delta==0: return Decimal(0)
 p=s.get(Product,p.id,with_for_update=True);amt=(abs(delta)*D(p.avg_cost)).quantize(Q2)
 if amt<=0: return Decimal(0)
 o=OPEN_EQ if opening else INV_ADJ
 L=[{'code':INVT,'debit':amt},{'code':o,'credit':amt}] if delta>0 else [{'code':o,'debit':amt},{'code':INVT,'credit':amt}]
 post_entry(s,cid,uid,('ورود' if delta>0 else 'خروج')+f' موجودی ({ref}) با بهای میانگین',L);return amt
def _gross_posted(s,cid,inv):
 e=source_entry(s,cid,'invoice',inv.id)
 return bool(e) and s.scalar(select(JournalLine.id).join(Account,Account.id==JournalLine.account_id).where(JournalLine.entry_id==e.id,Account.code==SDISC)) is not None
def make_return(s,cid,uid,o,inv,items,reason,restock):
 lines={l.product_id:l for l in s.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id==inv.id))}
 if not lines: raise HTTPException(409,'فاکتور فاقد سطر است')
 prior={pid:D(q) for pid,q in s.execute(select(SalesReturnLine.product_id,func.sum(SalesReturnLine.quantity)).join(SalesReturn,SalesReturn.id==SalesReturnLine.return_id).where(SalesReturn.invoice_id==inv.id).group_by(SalesReturnLine.product_id))}
 agg={}
 for pid,q in items: agg[pid]=agg.get(pid,Decimal(0))+D(q)
 prepared=[];net=Decimal(0)
 for pid,q in agg.items():
  l=lines.get(pid)
  if not l: raise HTTPException(400,'کالا در فاکتور وجود ندارد')
  if q>D(l.quantity)-prior.get(pid,Decimal(0)): raise HTTPException(400,'مقدار برگشت بیش از مقدار قابل برگشت است')
  amt=(D(l.line_total)*q/D(l.quantity)).quantize(Q2);net+=amt;prepared.append((pid,q,amt))
 tax=(net*D(inv.tax)/D(inv.subtotal)).quantize(Q2) if D(inv.subtotal)>0 else Decimal(0);total=net+tax
 if total<=0: raise HTTPException(400,'مبلغ برگشت نامعتبر است')
 r=SalesReturn(company_id=cid,number=num('SR',SalesReturn,s),order_id=o.id,invoice_id=inv.id,subtotal=net,tax=tax,total=total,reason=reason,restocked=restock,created_by=uid);s.add(r);s.flush()
 gross=_gross_posted(s,cid,inv);disc_total=cost_total=Decimal(0)
 for pid,q,amt in prepared:
  s.add(SalesReturnLine(return_id=r.id,product_id=pid,quantity=q,amount=amt));l=lines[pid]
  if gross: disc_total+=split_return_discount(l.unit_price,q,amt)
  if restock:
   p=s.get(Product,pid,with_for_update=True);unit=D(l.unit_cost)
   if unit>0: apply_receipt_cost(s,p,q,unit);c=(q*unit).quantize(Q2);cost_total+=c;l.cogs=max(Decimal(0),D(l.cogs)-c)
   st=s.scalar(select(Stock).where(Stock.warehouse_id==o.warehouse_id,Stock.product_id==pid).with_for_update()) or Stock(warehouse_id=o.warehouse_id,product_id=pid,quantity=0,reserved=0);s.add(st);st.quantity+=q
   s.add(StockMove(company_id=cid,warehouse_id=o.warehouse_id,product_id=pid,kind='return_in',quantity=q,unit_cost=unit if unit>0 else None,reference=r.number,user_id=uid))
 post_entry(s,cid,uid,f'برگشت از فروش {r.number} / فاکتور {inv.number}',[{'code':SALES,'debit':net+disc_total},{'code':SDISC,'credit':disc_total},{'code':VAT,'debit':tax},{'code':AR,'credit':total,'customer_id':o.customer_id},{'code':INVT,'debit':cost_total},{'code':COGS,'credit':cost_total}],source=('sales_return',r.id))
 inv.returned=D(inv.returned)+total;refresh_invoice_status(inv);return r
def entry_dict(s,e):
 d=obj(e);d['lines']=[{'account_code':a.code,'account_name':a.name,'debit':l.debit,'credit':l.credit,'customer_id':l.customer_id,'supplier_id':l.supplier_id,'memo':l.memo} for l,a in s.execute(select(JournalLine,Account).join(Account,Account.id==JournalLine.account_id).where(JournalLine.entry_id==e.id).order_by(JournalLine.id))];return d
def backfill_ledger():
 with SessionLocal() as s:
  if s.get(Sequence,'ledger_backfill_v1'): return
  for inv in s.scalars(select(Invoice).where(Invoice.status!='cancelled')).all():
   if not source_entry(s,inv.company_id,'invoice',inv.id): post_entry(s,inv.company_id,None,f'فاکتور فروش {inv.number} (انتقال)',invoice_lines(inv,s.get(Order,inv.order_id).customer_id),source=('invoice',inv.id))
  for p in s.scalars(select(Payment)).all():
   if source_entry(s,p.company_id,'payment',p.id): continue
   if not p.customer_id and not p.supplier_id and p.invoice_id: p.customer_id=s.get(Order,s.get(Invoice,p.invoice_id).order_id).customer_id
   if p.customer_id or p.supplier_id:
    d,L=payment_lines(s,p);post_entry(s,p.company_id,None,d+' (انتقال)',L,source=('payment',p.id))
  for po in s.scalars(select(Purchase).where(Purchase.status=='received')).all():
   if not source_entry(s,po.company_id,'purchase',po.id) and not source_entry(s,po.company_id,'purchase_receipt',po.id): post_entry(s,po.company_id,None,f'رسید خرید {po.number} (انتقال)',purchase_lines(po),source=('purchase',po.id))
  for c in s.scalars(select(Check)).all():
   if D(c.amount)<=0: continue
   if not source_entry(s,c.company_id,'check_created',c.id):
    post_entry(s,c.company_id,None,f'ثبت چک {c.number} (انتقال)',check_create_lines(c),source=('check_created',c.id))
    if c.status in ('cleared','bounced','cancelled','returned'): post_check_status(s,c.company_id,None,c,c.status)
  s.add(Sequence(key='ledger_backfill_v1',value=1));s.commit()
def price_quote(s,cid,pid,group='',qty=1):
 """قیمت قابل‌توضیح: قانون‌های فعال/در بازه/متناسب با گروه و حداقل تعداد؛ ارزان‌ترین قانونِ اختصاصی گروه (وگرنه عمومی) برنده است"""
 p=s.get(Product,pid);now=utcnow();qty=D(qty) if qty else Decimal(1)
 rules=[r for r in s.scalars(select(PriceRule).where(PriceRule.company_id==cid,PriceRule.product_id==pid,PriceRule.active==True)).all() if r.customer_group in ('',group or '') and (not r.starts_at or r.starts_at<=now) and (not r.ends_at or r.ends_at>=now) and D(r.min_qty or 1)<=qty]
 def val(r): return (r.price if r.price is not None else p.base_price*(Decimal(1)-r.discount_percent/Decimal(100)))
 camps=[c for c in s.scalars(select(Campaign).where(Campaign.company_id==cid,Campaign.active==True)).all() if c.product_id in (None,pid) and c.customer_group in ('',group or '') and (not c.starts_at or c.starts_at<=now) and (not c.ends_at or c.ends_at>=now) and D(c.min_qty or 1)<=qty]
 cbest=min(camps,key=lambda c:p.base_price*(Decimal(1)-D(c.discount_percent)/Decimal(100))) if camps else None
 cval=(p.base_price*(Decimal(1)-D(cbest.discount_percent)/Decimal(100))).quantize(Decimal('0.01')) if cbest else None
 if not rules:
  if cbest: return {'price':cval,'base_price':p.base_price,'rule_id':None,'campaign_id':cbest.id,'reason':f'کمپین «{cbest.name}» · {D(cbest.discount_percent):g}٪ تخفیف'}
  return {'price':p.base_price,'base_price':p.base_price,'rule_id':None,'campaign_id':None,'reason':'قیمت پایه'}
 specific=[r for r in rules if r.customer_group and r.customer_group==(group or '')]
 best=min(specific or rules,key=val)
 if cbest and cval<val(best): return {'price':cval,'base_price':p.base_price,'rule_id':None,'campaign_id':cbest.id,'reason':f'کمپین «{cbest.name}» · {D(cbest.discount_percent):g}٪ تخفیف'}
 why=('قیمت ثابت' if best.price is not None else f'{best.discount_percent}٪ تخفیف')+(f' · گروه {best.customer_group}' if best.customer_group else ' · عمومی')+(f' · از {D(best.min_qty):g} عدد به بالا' if D(best.min_qty or 1)>1 else '')
 return {'price':val(best),'base_price':p.base_price,'rule_id':best.id,'campaign_id':None,'reason':why}
def effective_price(s,cid,pid,group='',qty=1): return price_quote(s,cid,pid,group,qty)['price']
INVOICE_FLOW={'open':{'partial','paid','cancelled'},'partial':{'open','paid','cancelled'},'paid':{'partial','open'},'cancelled':set()}
def set_invoice_status(inv,new):
 if new==inv.status: return
 if new not in INVOICE_FLOW.get(inv.status,set()): raise HTTPException(409,f'انتقال وضعیت فاکتور از {inv.status} به {new} مجاز نیست')
 inv.status=new
def vat_percent(s,cid):
 v=s.scalar(select(Setting.value).where(Setting.company_id==cid,Setting.key=='vat_percent'))
 try: return Decimal(v) if v not in (None,'') else Decimal(0)
 except Exception: return Decimal(0)
def _jl_q(cid,types,start=None,end=None,closing=False):
 q=select(Account.code,Account.name,Account.type,func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).select_from(JournalLine).join(Account,Account.id==JournalLine.account_id).join(JournalEntry,JournalEntry.id==JournalLine.entry_id).where(JournalLine.company_id==cid,Account.type.in_(types))
 if not closing: q=q.where(or_(JournalEntry.source_type.is_(None),JournalEntry.source_type!='year_close'))   # سند اختتامیه در سود و زیان دوره دیده نمی‌شود
 if start: q=q.where(JournalEntry.entry_date>=start)
 if end: q=q.where(JournalEntry.entry_date<=end)
 return q.group_by(Account.id,Account.code,Account.name,Account.type).order_by(Account.code)
def _range(start,end):
 if start and end and start>end: raise HTTPException(400,'بازه‌ی تاریخ نامعتبر است')
