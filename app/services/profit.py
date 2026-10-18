"""گزارش سود ناخالص: از سطرهای فاکتورِ «تحویل‌شده» (درآمد و بها هر دو محقق شده‌اند) و بهای ثبت‌شده‌ی هر سطر.

- درآمد = line_total − برگشتی‌های همان کالا/فاکتور (بدون مالیات و بدون حمل)
- بها = InvoiceLine.cogs (بهای میانگین لحظه‌ی خروج، منهای برگشتی‌های وارد انبار)
- فاکتورهای تأییدشده‌ی هنوز تحویل‌نشده در `in_transit_revenue` جدا می‌آیند تا سود را باد نکنند.
"""
from __future__ import annotations
from decimal import Decimal
from sqlalchemy import func,select
from app.core.common import D,Q2
from app.models import Account,Customer,Invoice,InvoiceLine,JournalEntry,JournalLine,Order,Product,SalesReturn,SalesReturnLine,User
from app.services.accounting import COGS,SDISC,SALES

BY={'product','customer','seller','region'}
def _pct(a,b): return (a*100/b).quantize(Q2) if b else Decimal(0)
def profit_lines(s,cid,start=None,end=None):
 q=select(InvoiceLine,Invoice,Order,Customer,Product,User).join(Invoice,Invoice.id==InvoiceLine.invoice_id).join(Order,Order.id==Invoice.order_id).join(Customer,Customer.id==Order.customer_id).join(Product,Product.id==InvoiceLine.product_id).join(User,User.id==Order.seller_id).where(Invoice.company_id==cid,Invoice.status!='cancelled')
 if start: q=q.where(func.date(Invoice.issued_at)>=start)
 if end: q=q.where(func.date(Invoice.issued_at)<=end)
 rets={(i,p):(D(qy),D(a)) for i,p,qy,a in s.execute(select(SalesReturn.invoice_id,SalesReturnLine.product_id,func.sum(SalesReturnLine.quantity),func.sum(SalesReturnLine.amount)).join(SalesReturn,SalesReturn.id==SalesReturnLine.return_id).where(SalesReturn.company_id==cid).group_by(SalesReturn.invoice_id,SalesReturnLine.product_id))}
 out=[];transit=Decimal(0)
 for l,inv,o,c,p,u in s.execute(q):
  rq,ra=rets.get((inv.id,l.product_id),(Decimal(0),Decimal(0)));qty=D(l.quantity);revenue=D(l.line_total)-ra
  if o.status!='delivered': transit+=revenue;continue
  disc=D(l.discount)*(1-rq/qty) if qty>0 else Decimal(0);cogs=D(l.cogs)
  out.append({'product_id':p.id,'product':p.name,'sku':p.sku,'customer_id':c.id,'customer':c.name,'region':c.region or '—','seller_id':u.id,'seller':u.name,'invoice_id':inv.id,'invoice':inv.number,'quantity':qty-rq,'gross_sales':(revenue+disc).quantize(Q2),'discount':disc.quantize(Q2),'revenue':revenue.quantize(Q2),'cogs':cogs.quantize(Q2),'profit':(revenue-cogs).quantize(Q2),'costed':D(l.unit_cost)>0})
 return out,transit
def _bal(s,cid,code,kind):
 d,c=s.execute(select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).join(Account,Account.id==JournalLine.account_id).where(JournalLine.company_id==cid,Account.code==code)).one()
 return D(d)-D(c) if kind=='debit' else D(c)-D(d)
def summarize(rows,transit):
 rev=sum((x['revenue'] for x in rows),Decimal(0));cogs=sum((x['cogs'] for x in rows),Decimal(0));disc=sum((x['discount'] for x in rows),Decimal(0));gs=sum((x['gross_sales'] for x in rows),Decimal(0))
 return {'gross_sales':gs,'discount':disc,'revenue':rev,'cogs':cogs,'gross_profit':rev-cogs,'margin_percent':_pct(rev-cogs,rev),'in_transit_revenue':transit,'uncosted_lines':sum(1 for x in rows if not x['costed'])}
def profit_report(s,cid,by='product',start=None,end=None):
 rows,transit=profit_lines(s,cid,start,end);g={}
 for x in rows:
  k=x[{'product':'product_id','customer':'customer_id','seller':'seller_id','region':'region'}[by]]
  r=g.setdefault(k,{'key':k,'name':x[by] if by!='product' else f"{x['sku']} — {x['product']}",'quantity':Decimal(0),'gross_sales':Decimal(0),'discount':Decimal(0),'revenue':Decimal(0),'cogs':Decimal(0),'profit':Decimal(0)})
  for f in ('quantity','gross_sales','discount','revenue','cogs','profit'): r[f]+=x[f]
 items=sorted(g.values(),key=lambda r:r['profit'],reverse=True)
 for r in items: r['margin_percent']=_pct(r['profit'],r['revenue'])
 out={'by':by,'start':start,'end':end,'items':items,'summary':summarize(rows,transit)}
 if not start and not end:   # تطبیق با دفتر فقط برای کل دوره معنادار است (تاریخ فاکتور ≠ تاریخ سند بها)
  lc=_bal(s,cid,COGS,'debit');out['ledger']={'cogs':lc,'cogs_matches_lines':abs(lc-out['summary']['cogs'])<=Q2,'net_sales':_bal(s,cid,SALES,'credit')-_bal(s,cid,SDISC,'debit')}
 return out
