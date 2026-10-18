"""داشبورد مدیرعامل: KPIها از دیتابیس/دفتر کل، نقدینگی، چک‌ها، عملکرد کارکنان و تجمیع شرکت‌های هلدینگ.

هر KPI یک `drill` دارد (گزارش/پارامتر) تا عدد داشبورد به گزارش و سپس سند حسابداری قابل پیگیری باشد.
Consolidation: جمع ساده‌ی شرکت‌های هم‌گروه که کاربر عضو آن‌هاست. ⚠️ معاملات بین‌شرکتی مدل نشده‌اند،
پس حذف (elimination) انجام نمی‌شود و در خروجی هشدار می‌آید.
"""
from __future__ import annotations
from datetime import date,timedelta
from decimal import Decimal
from sqlalchemy import func,select
from app.core.common import D,Q2
from app.models import Company,Customer,Delivery,Invoice,JournalLine,Membership,Order,Payment,Product,Stock
from app.services.accounting import AP,AR,BANK,CASH,COGS,INVT,party_balances
from app.services.profit import profit_lines,summarize
from app.services.reports import checks_buckets,ledger_amount

def _sum(rows): return sum(rows,Decimal(0))
def _drill(report,**p): return {'report':report,'params':p}
def company_kpis(s,cid,flags,today=None):
 """flags: مجموعه‌ای از ماژول‌های مجاز ('sales','finance','inventory','crm','delivery'). بخش بدون مجوز None می‌ماند."""
 today=today or date.today();m1=today.replace(day=1);k={}
 if 'sales' in flags:
  def tot(a,b): return D(s.scalar(select(func.coalesce(func.sum(Order.total),0)).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)>=a,func.date(Order.created_at)<=b)))
  k['sales_today']={'value':tot(today,today),'drill':_drill('sales',by='customer',start=today.isoformat(),end=today.isoformat())}
  k['sales_month']={'value':tot(m1,today),'drill':_drill('sales',by='day',start=m1.isoformat(),end=today.isoformat())}
  k['orders_today']={'value':s.scalar(select(func.count()).select_from(Order).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)==today)) or 0,'drill':_drill('sales',by='seller',start=today.isoformat(),end=today.isoformat())}
 if 'finance' in flags:
  rows,transit=profit_lines(s,cid,m1,today);sm=summarize(rows,transit)
  k['gross_profit_month']={'value':sm['gross_profit'],'margin_percent':sm['margin_percent'],'in_transit_revenue':sm['in_transit_revenue'],'uncosted_lines':sm['uncosted_lines'],'drill':_drill('profit',by='product',start=m1.isoformat(),end=today.isoformat())}
  k['receivables']={'value':_sum(party_balances(s,cid,'customer').values()),'drill':_drill('aging')}
  k['payables']={'value':_sum(party_balances(s,cid,'supplier').values()),'drill':{'report':'general-ledger','params':{'account_code':AP}}}
  cash=ledger_amount(s,cid,CASH,'debit');bank=ledger_amount(s,cid,BANK,'debit')
  k['cash']={'value':cash+bank,'cash':cash,'bank':bank,'drill':{'report':'general-ledger','params':{'account_code':BANK}}}
  k['payments_today']={'value':D(s.scalar(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.company_id==cid,Payment.kind=='receipt',func.date(Payment.created_at)==today))),'drill':_drill('finance')}
  b=checks_buckets(s,cid,today);r=b['received'];p=b['paid']
  k['checks']={'received':r,'paid':p,'drill':{'page':'treasury'}}
  def horizon(days):
   inc=r['overdue']['amount']+r['d7']['amount']+(r['d30']['amount'] if days>7 else Decimal(0));out=p['overdue']['amount']+p['d7']['amount']+(p['d30']['amount'] if days>7 else Decimal(0))
   return {'days':days,'inflow':inc,'outflow':out,'projected':cash+bank+inc-out}
  k['liquidity']={'cash_now':cash+bank,'forecast':[horizon(7),horizon(30)],'note':'پیش‌بینی = نقد و بانک + چک‌های دریافتیِ باز (شامل سررسیدگذشته) − چک‌های پرداختیِ باز؛ دریافت از حساب مشتریان در نظر گرفته نشده.','drill':{'report':'general-ledger','params':{'account_code':CASH}}}
 if 'inventory' in flags:
  k['stock_value']={'value':D(s.scalar(select(func.coalesce(func.sum(Stock.quantity*Product.avg_cost),0)).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid))),'unvalued_products':s.scalar(select(func.count(func.distinct(Product.id))).select_from(Stock).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid,Stock.quantity>0,Product.avg_cost<=0)) or 0,'drill':_drill('inventory',kind='stock')}
  k['low_stock']={'value':s.scalar(select(func.count()).select_from(Stock).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid,Product.min_stock>0,Stock.quantity-Stock.reserved<=Product.min_stock)) or 0,'drill':_drill('inventory',kind='low')}
 if 'crm' in flags: k['customers']={'value':s.scalar(select(func.count()).select_from(Customer).where(Customer.company_id==cid,Customer.active==True)) or 0,'drill':_drill('customers')}
 if 'delivery' in flags: k['active_deliveries']={'value':s.scalar(select(func.count()).select_from(Delivery).where(Delivery.company_id==cid,Delivery.status.in_(['assigned','out_for_delivery']))) or 0,'drill':_drill('drivers')}
 return k
def holding_companies(s,u,cid):
 """شرکت‌های فعالِ هم‌گروه با شرکت جاری که کاربر عضو آن‌هاست"""
 gid=s.scalar(select(Company.group_id).where(Company.id==cid))
 return s.scalars(select(Company).where(Company.group_id==gid,Company.active==True,Company.id.in_(select(Membership.company_id).where(Membership.user_id==u.id))).order_by(Company.id)).all()
SUM_KEYS=('sales_today','sales_month','orders_today','gross_profit_month','receivables','payables','cash','payments_today','stock_value','low_stock','customers','active_deliveries')
def consolidate(per):
 tot={}
 for key in SUM_KEYS:
  vals=[x['kpis'][key]['value'] for x in per if x['kpis'].get(key)]
  if vals: tot[key]=_sum([D(v) for v in vals]) if not isinstance(vals[0],int) else sum(vals)
 return tot
def reconcile(s,cid):
 """بررسی‌های تطبیق عددهای داشبورد با دفتر کل (برای drill-down و اعتماد به داده)"""
 d,c=s.execute(select(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).where(JournalLine.company_id==cid)).one();d=D(d);c=D(c)
 rows,_=profit_lines(s,cid);lines_cogs=_sum([x['cogs'] for x in rows])
 led_cogs=ledger_amount(s,cid,COGS,'debit')
 stock=D(s.scalar(select(func.coalesce(func.sum(Stock.quantity*Product.avg_cost),0)).join(Product,Product.id==Stock.product_id).where(Product.company_id==cid)))
 led_inv=ledger_amount(s,cid,INVT,'debit');ar=ledger_amount(s,cid,AR,'debit');recv=_sum(party_balances(s,cid,'customer').values())
 inv_open=_sum([D(i.total)-D(i.returned)-D(i.paid) for i in s.scalars(select(Invoice).where(Invoice.company_id==cid,Invoice.status.in_(['open','partial'])))])
 def chk(name,a,b,note=''): return {'name':name,'a':a,'b':b,'diff':a-b,'ok':abs(a-b)<=Q2,'note':note}
 return [chk('تراز آزمایشی: جمع بدهکار = جمع بستانکار',d,c),chk('بهای تمام‌شده: دفتر (۵۱۰۰) = جمع بهای سطرهای فاکتور',led_cogs,lines_cogs,'اختلاف معمولاً از فاکتورهای قبل از ثبت بها است'),chk('مانده مشتریان (ریز تفصیلی) = حساب دریافتنی کل (۱۲۱۰)',recv,ar),chk('موجودی کالا: انبار (بر پایه بها) = دفتر (۱۳۱۰)',stock,led_inv,'اختلاف یعنی موجودی/تعدیل بدون سند یا بهای ثبت‌نشده'),chk('فاکتورهای باز = مانده مشتریان',inv_open,recv,'تفاوت = پرداخت علی‌الحساب یا مانده اول دوره')]
def sales_series(s,cid,days,user_id=None):
 start=date.today()-timedelta(days=days-1)
 q=select(func.date(Order.created_at),func.sum(Order.total)).where(Order.company_id==cid,Order.status!='cancelled',func.date(Order.created_at)>=start)
 if user_id: q=q.where(Order.seller_id==user_id)
 m={str(d):D(v) for d,v in s.execute(q.group_by(func.date(Order.created_at)))}
 return [{'day':str(start+timedelta(i)),'total':m.get(str(start+timedelta(i)),Decimal(0))} for i in range(days)]
