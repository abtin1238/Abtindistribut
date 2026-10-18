from __future__ import annotations
from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.security import has_perm, has_all
from app.modules.automation import performance
from app.services.ceo import company_kpis, consolidate, holding_companies, reconcile, sales_series
from app.services.reports import drivers_report, sales_report, visitors_report

MODS=(('sales','sales.read'),('finance','finance.read'),('inventory','inventory.read'),('crm','crm.read'),('delivery','delivery.read'))

def _flags(r): return {m for m,p in MODS if has_perm(r,p)}

def _ceo(ctx):
 """داشبورد مدیرعامل جمع‌بندی کل شرکت است و دسترسی اختصاصی `ceo.read` می‌خواهد.
 `data.all` فقط یعنی «داده‌ی همه را ببین» (مثلاً حسابدار/انباردار هم دارند) و به‌تنهایی اجازه‌ی ورود به این داشبورد نیست؛ هر دو لازم است."""
 if not (has_perm(ctx[2],'ceo.read') and has_all(ctx[2])): raise HTTPException(403,'داشبورد مدیرعامل فقط برای نقش‌های دارای دسترسی «ceo.read» است')

def _top(rows,n=5): return rows[:n]

def summary(ctx, s: Session):
 _ceo(ctx);u,cid,r=ctx;today=date.today();m1=today.replace(day=1);fl=_flags(r);p={'start':m1,'end':today}
 out={'date':today,'month_start':m1,'kpis':company_kpis(s,cid,fl,today),'tops':{},'staff':{}}
 if 'sales' in fl:
  for by in ('product','customer'): out['tops'][by]=_top(sales_report(s,ctx,{**p,'by':by})['rows'])
  out['staff']['sellers']=_top(sales_report(s,ctx,{**p,'by':'seller'})['rows'],8)
  out['staff']['targets']=performance(s,cid,f'{today.year:04d}-{today.month:02d}',None)
 if has_perm(r,'visit.read'): out['staff']['visitors']=_top(visitors_report(s,ctx,p)['rows'],8)
 if 'delivery' in fl: out['staff']['drivers']=_top(drivers_report(s,ctx,p)['rows'],8)
 return out

def trend(days: int, ctx, s: Session):
 _ceo(ctx)
 if not has_perm(ctx[2],'sales.read'): raise HTTPException(403,'دسترسی کافی نیست')
 return {'days':days,'series':sales_series(s,ctx[1],days)}

def holding(ctx, s: Session):
 """مقایسه و تجمیع (Consolidation) شرکت‌های هم‌گروه که کاربر عضو آن‌هاست"""
 _ceo(ctx);u,cid,r=ctx;fl=_flags(r);today=date.today();per=[]
 for c in holding_companies(s,u,cid): per.append({'company_id':c.id,'name':c.name,'code':c.code,'current':c.id==cid,'kpis':company_kpis(s,c.id,fl,today)})
 tot=consolidate(per);warn=['جمع ساده‌ی شرکت‌هاست؛ معاملات بین‌شرکتی مدل نشده‌اند و حذف (elimination) انجام نمی‌شود.']
 if len(per)<2: warn.append('فقط یک شرکت عضو این گروه در دسترس شما است.')
 return {'companies':per,'consolidated':tot,'warnings':warn}

def recon(ctx, s: Session):
 _ceo(ctx)
 if not has_perm(ctx[2],'finance.read'): raise HTTPException(403,'دسترسی کافی نیست')
 c=reconcile(s,ctx[1]);return {'checks':c,'all_ok':all(x['ok'] for x in c)}
