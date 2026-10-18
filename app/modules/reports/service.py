from __future__ import annotations
import os
from datetime import date, timedelta
from typing import Literal, Optional
from fastapi import BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import audit, obj, D
from app.core.security import has_perm
from app.models import Company, ReportJob, Role, User
from app.modules.finance import xlsx_response, aging
from app.services.profit import BY, profit_report
from app.services.reports import make_filter, sales_detail, col, customers_report, drivers_report, finance_report, inventory_report, sales_report, visitors_report, _table
from .schemas import JobIn
import logging
from uuid import uuid4
from app.core.config import ROOT, utcnow
from app.core.database import SessionLocal
from app.services.exporters import to_pdf, to_xlsx

log=logging.getLogger('abtin')

JOB_TTL_DAYS=7;MAX_ACTIVE_JOBS=3;MAX_SYNC_ROWS=5000





def _by(by):
 if by not in BY: raise HTTPException(400,'مبنای گزارش نامعتبر است (product/customer/seller/region)')
 return by

# ---------------------------------------------------------------- گزارش‌های جدولی استاندارد
def profit_table(s,ctx,params):
 f=make_filter(ctx,params);by=_by(params.get('by') or 'product');d=profit_report(s,ctx[1],by,f.start,f.end);sm=d['summary']
 rows=[{'_key':str(x['key']),'name':x['name'],'quantity':x['quantity'],'gross_sales':x['gross_sales'],'discount':x['discount'],'revenue':x['revenue'],'cogs':x['cogs'],'profit':x['profit'],'margin_percent':x['margin_percent']} for x in d['items']]
 cols=[col('name',{'product':'کالا','customer':'مشتری','seller':'فروشنده','region':'منطقه'}[by]),col('quantity','تعداد','qty'),col('gross_sales','فروش ناخالص','money'),col('discount','تخفیف','money'),col('revenue','درآمد خالص','money'),col('cogs','بهای تمام‌شده','money'),col('profit','سود ناخالص','money'),col('margin_percent','حاشیه ٪','pct')]
 summ=[['درآمد خالص',sm['revenue'],'money'],['بهای تمام‌شده',sm['cogs'],'money'],['سود ناخالص',sm['gross_profit'],'money'],['حاشیه ناخالص',sm['margin_percent'],'pct'],['درآمد فاکتورهای تحویل‌نشده (در راه)',sm['in_transit_revenue'],'money'],['سطرهای بدون بها',sm['uncosted_lines'],'int']]
 return _table('گزارش سود ناخالص',cols,rows,summ,f)

def aging_table(s,ctx,params):
 f=make_filter(ctx,params);d=aging(f.end,ctx,s);t=d['totals']
 rows=[{'_key':str(x['customer_id']),'code':x['code'],'customer':x['customer'],'b0_30':x['b0_30'],'b31_60':x['b31_60'],'b61_90':x['b61_90'],'b90p':x['b90p'],'invoices_total':x['invoices_total'],'ledger_balance':x['ledger_balance'],'unallocated':x['unallocated']} for x in d['rows']]
 rows.sort(key=lambda x:-D(x['invoices_total']))
 cols=[col('code','کد'),col('customer','مشتری'),col('b0_30','۰–۳۰ روز','money'),col('b31_60','۳۱–۶۰','money'),col('b61_90','۶۱–۹۰','money'),col('b90p','بیش از ۹۰','money'),col('invoices_total','جمع فاکتورهای باز','money'),col('ledger_balance','مانده دفتر','money'),col('unallocated','علی‌الحساب/تفاوت','money')]
 return _table('بدهکاران و Aging',cols,rows,[['جمع فاکتورهای باز',t['invoices_total'],'money'],['بیش از ۹۰ روز',t['b90p'],'money'],['مانده دفتر',t['ledger_balance'],'money']],f)

REG={'sales':('sales.read','گزارش فروش',sales_report),'customers':('crm.read','گزارش مشتریان',customers_report),'inventory':('inventory.read','گزارش انبار',inventory_report),'visitors':('visit.read','عملکرد بازاریاب',visitors_report),'drivers':('delivery.read','عملکرد مأمور پخش',drivers_report),'profit':('finance.read','سود ناخالص',profit_table),'aging':('finance.read','بدهکاران و Aging',aging_table),'finance':('finance.read','گزارش مالی',finance_report)}

def run_report(name,s,ctx,params):
 if name not in REG: raise HTTPException(404,'گزارش یافت نشد')
 perm,_,fn=REG[name]
 if not has_perm(ctx[2],perm): raise HTTPException(403,'دسترسی کافی نیست')
 return fn(s,ctx,params)

def _render(t,fmt,company=''):
 if fmt=='xlsx': return to_xlsx(t),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 if fmt=='pdf': return to_pdf(t,company),'application/pdf'
 raise HTTPException(400,'قالب خروجی باید xlsx یا pdf باشد')

def _job_view(j): return {k:v for k,v in obj(j).items() if k!='path'}

def run_job(job_id:int):
 """اجرای یک کار صف (در thread پس‌زمینه با نشست مستقل). خطا هرگز بیرون نمی‌پرد؛ وضعیت failed با پیام ثبت می‌شود."""
 with SessionLocal() as s:
  j=s.get(ReportJob,job_id)
  if not j or j.status!='queued': return
  j.status='running';s.commit()
  try:
   u=s.get(User,j.user_id);r=s.get(Role,u.role_id) if u else None
   if not u or not u.active: raise HTTPException(403,'کاربر غیرفعال است')
   t=run_report(j.report,s,(u,j.company_id,r),dict(j.params or {}));co=s.get(Company,j.company_id)
   data,_=_render(t,j.fmt,co.name if co else '')
   d=os.path.join(ROOT,'uploads',str(j.company_id),'reports');os.makedirs(d,exist_ok=True);p=os.path.join(d,uuid4().hex+'.'+j.fmt)
   with open(p,'wb') as fh: fh.write(data)
   j.path=p;j.title=t['title'];j.filename=f'{j.report}-{date.today()}.{j.fmt}';j.status='done'
  except HTTPException as e: s.rollback();j=s.get(ReportJob,job_id);j.status='failed';j.error=str(e.detail)[:500]
  except Exception as e:
   s.rollback();log.exception('report job %s failed',job_id);j=s.get(ReportJob,job_id);j.status='failed';j.error=(str(e) or e.__class__.__name__)[:500]
  j.finished_at=utcnow();s.commit()

def _own_job(s,ctx,jid):
 j=s.get(ReportJob,jid)
 if not j or j.company_id!=ctx[1] or j.user_id!=ctx[0].id: raise HTTPException(404,'کار یافت نشد')
 return j

def fail_orphan_jobs(s):
 """در راه‌اندازی: کارهای نیمه‌کاره‌ی پیش از ری‌استارت را ناموفق علامت بزن تا کاربر دوباره درخواست دهد"""
 n=0
 for j in s.scalars(select(ReportJob).where(ReportJob.status.in_(['queued','running']))): j.status='failed';j.error='سرور در حین ساخت راه‌اندازی مجدد شد؛ دوباره درخواست دهید';j.finished_at=utcnow();n+=1
 s.commit();return n

def purge_jobs(s,days:int=JOB_TTL_DAYS):
 """حذف فایل و ردیف کارهای قدیمی (فایل خروجی داده‌ی مشتق است، حذف فیزیکی آن مجاز)"""
 n=0
 for j in s.scalars(select(ReportJob).where(ReportJob.created_at<utcnow()-timedelta(days=days))):
  if j.path:
   try: os.remove(j.path)
   except FileNotFoundError: pass
   except OSError: log.exception('report file delete failed');continue
  s.delete(j);n+=1
 s.commit();return n

def profit_breakdown(by: str, start: Optional[date], end: Optional[date], ctx, s: Session):
 if start and end and start>end: raise HTTPException(400,'بازه‌ی تاریخ نامعتبر است')
 return profit_report(s,ctx[1],_by(by),start,end)

def profit_breakdown_xlsx(by: str, start: Optional[date], end: Optional[date], ctx, s: Session):
 d=profit_breakdown(by,start,end,ctx,s);sm=d['summary']
 rows=[[x['name'],x['quantity'],x['gross_sales'],x['discount'],x['revenue'],x['cogs'],x['profit'],x['margin_percent']] for x in d['items']]
 rows.append(['جمع',None,sm['gross_sales'],sm['discount'],sm['revenue'],sm['cogs'],sm['gross_profit'],sm['margin_percent']])
 return xlsx_response('gross-profit-'+d['by'],['عنوان','تعداد','فروش ناخالص','تخفیف','درآمد خالص','بهای تمام‌شده','سود ناخالص','حاشیه ٪'],rows)

def catalog(ctx, s: Session):
 return {'reports':[{'name':n,'title':t,'permission':p} for n,(p,t,_f) in REG.items() if has_perm(ctx[2],p)],
 'options':{'sales_by':['product','customer','seller','region','branch','day','category'],'inventory_kind':['stock','low','dead','movement'],'profit_by':sorted(BY)},
 'filters':['start','end','jstart','jend','user_id','branch_id','region','warehouse_id','days']}

def run(name: str, request: Request, ctx, s: Session):
 return run_report(name,s,ctx,dict(request.query_params))

def sales_drill(request: Request, ctx, s: Session):
 if not has_perm(ctx[2],'sales.read'): raise HTTPException(403,'دسترسی کافی نیست')
 return sales_detail(s,ctx,dict(request.query_params))

def export(name: str, request: Request, format: Literal['xlsx', 'pdf'], ctx, s: Session):
 """خروجی هم‌زمان برای گزارش‌های کوچک؛ گزارش بزرگ باید با /api/reports/jobs در صف ساخته شود"""
 params={k:v for k,v in request.query_params.items() if k!='format'};t=run_report(name,s,ctx,params)
 if len(t['rows'])>MAX_SYNC_ROWS: raise HTTPException(413,f'گزارش بیش از {MAX_SYNC_ROWS} ردیف است؛ از خروجی پس‌زمینه (/api/reports/jobs) استفاده کنید')
 co=s.get(Company,ctx[1])
 try: data,mt=_render(t,format,co.name if co else '')
 except RuntimeError as e: raise HTTPException(501,str(e))
 audit(s,ctx[1],ctx[0].id,'export','report',None,{'report':name,'format':format,'params':params,'rows':len(t['rows'])});s.commit()
 return Response(data,media_type=mt,headers={'Content-Disposition':f'attachment; filename={name}-{date.today()}.{format}','X-Content-Type-Options':'nosniff'})

def job_create(x: JobIn, bg: BackgroundTasks, ctx, s: Session):
 u,cid,r=ctx
 if x.report not in REG: raise HTTPException(404,'گزارش یافت نشد')
 if not has_perm(r,REG[x.report][0]): raise HTTPException(403,'دسترسی کافی نیست')
 if len(x.params)>20 or any(len(str(k))>40 or len(str(v))>200 for k,v in x.params.items()): raise HTTPException(400,'پارامترهای گزارش نامعتبر است')
 make_filter(ctx,{k:v for k,v in x.params.items()})   # اعتبارسنجی زودهنگام تاریخ/فیلترها
 active=len(s.scalars(select(ReportJob.id).where(ReportJob.company_id==cid,ReportJob.user_id==u.id,ReportJob.status.in_(['queued','running']))).all())
 if active>=MAX_ACTIVE_JOBS: raise HTTPException(429,'چند خروجی در حال ساخت دارید؛ کمی صبر کنید')
 j=ReportJob(company_id=cid,user_id=u.id,report=x.report,params=x.params,fmt=x.format,title=REG[x.report][1]);s.add(j);s.flush()
 audit(s,cid,u.id,'export_job','report',j.id,{'report':x.report,'format':x.format,'params':x.params});s.commit();bg.add_task(run_job,j.id);return _job_view(j)

def job_list(ctx, s: Session):
 return [_job_view(j) for j in s.scalars(select(ReportJob).where(ReportJob.company_id==ctx[1],ReportJob.user_id==ctx[0].id).order_by(ReportJob.id.desc()).limit(30))]

def job_get(jid: int, ctx, s: Session):
 return _job_view(_own_job(s, ctx, jid))

def job_download(jid: int, ctx, s: Session):
 j=_own_job(s,ctx,jid)
 if j.status!='done' or not j.path or not os.path.isfile(j.path): raise HTTPException(409 if j.status!='done' else 410,'فایل آماده نیست یا حذف شده است')
 return FileResponse(j.path,media_type='application/pdf' if j.fmt=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=j.filename,headers={'X-Content-Type-Options':'nosniff'})
