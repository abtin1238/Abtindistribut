from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.common import D, Q2, audit, list_json, obj, same_company
from app.core.config import utcnow
from app.models import Attendance, Company, Employee, EmployeeShift, LeaveRequest, PayrollLine, PayrollRun, Shift
from app.services.accounting import BANK, SAL_EXP, SAL_PAY, post_entry
from app.services.shifts import shift_metrics
from .schemas import EmployeeShiftIn, LeaveIn, PayrollRunIn, EmployeeIn, ShiftIn, ShiftPatch

LEAVE_KINDS={'annual':'استحقاقی','sick':'استعلاجی','unpaid':'بدون حقوق'}

DAYS_IN_MONTH=Decimal(30)   # قرارداد ساده: ماه ۳۰ روزه برای کسر حقوق

def _decide(lid,ctx,s,new):
 u,cid,r=ctx;q=same_company(s,LeaveRequest,lid,cid)
 if q.status!='pending': raise HTTPException(409,'این درخواست قبلاً تعیین تکلیف شده است')
 q.status=new;q.decided_by=u.id;q.decided_at=utcnow();audit(s,cid,u.id,new,'leave',q.id,{});s.commit();return obj(q)

def _unpaid_days(s,emp_id,first,last):
 """روزهای مرخصی بدون‌حقوقِ تأییدشده که در بازهٔ ماه می‌افتند"""
 n=0
 for l in s.scalars(select(LeaveRequest).where(LeaveRequest.employee_id==emp_id,LeaveRequest.status=='approved',LeaveRequest.kind=='unpaid',LeaveRequest.start_date<=last,LeaveRequest.end_date>=first)):
  n+=(min(l.end_date,last)-max(l.start_date,first)).days+1
 return n

def _run_dict(s,run):
 ls=s.scalars(select(PayrollLine).where(PayrollLine.run_id==run.id).order_by(PayrollLine.id)).all()
 names={e.id:e.name for e in s.scalars(select(Employee).where(Employee.id.in_([l.employee_id for l in ls]))).all()} if ls else {}
 return {**obj(run),'lines':[{**obj(l),'employee':names.get(l.employee_id,'')} for l in ls]}

def employees(ctx, s: Session):
 return [obj(x) for x in list_json(s, Employee, ctx[1])]

def add_employee(x: EmployeeIn, ctx, s: Session):
 u,cid,r=ctx;q=Employee(company_id=cid,**x.model_dump());s.add(q);audit(s,cid,u.id,'create','employee');s.commit();s.refresh(q);return obj(q)

def attendance_in(employee_id: int, ctx, s: Session):
 u,cid,r=ctx;e=s.get(Employee,employee_id)
 if not e or e.company_id!=cid:raise HTTPException(404,'کارمند یافت نشد')
 d=date.today();q=s.scalar(select(Attendance).where(Attendance.employee_id==e.id,Attendance.day==d))
 if q:raise HTTPException(400,'ورود امروز قبلاً ثبت شده')
 q=Attendance(company_id=cid,employee_id=e.id,day=d,check_in=utcnow());s.add(q);s.commit();return obj(q)

def attendance_out(employee_id: int, ctx, s: Session):
 u,cid,r=ctx;q=s.scalar(select(Attendance).where(Attendance.employee_id==employee_id,Attendance.day==date.today(),Attendance.company_id==cid))
 if not q:raise HTTPException(404,'ورود امروز یافت نشد')
 q.check_out=utcnow();s.commit();return obj(q)

def attendance(ctx, s: Session):
 return [obj(x) for x in list_json(s, Attendance, ctx[1])]

def leaves(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(LeaveRequest).where(LeaveRequest.company_id==ctx[1]).order_by(LeaveRequest.id.desc()).limit(500)).all()]

def add_leave(x: LeaveIn, ctx, s: Session):
 u,cid,r=ctx;e=s.get(Employee,x.employee_id)
 if not e or e.company_id!=cid: raise HTTPException(404,'کارمند یافت نشد')
 if x.kind not in LEAVE_KINDS: raise HTTPException(400,'نوع مرخصی نامعتبر است')
 if x.end_date<x.start_date: raise HTTPException(400,'پایان مرخصی قبل از شروع آن است')
 if s.scalar(select(LeaveRequest.id).where(LeaveRequest.employee_id==e.id,LeaveRequest.status.in_(('pending','approved')),LeaveRequest.start_date<=x.end_date,LeaveRequest.end_date>=x.start_date)): raise HTTPException(409,'برای این بازه مرخصی دیگری ثبت شده است')
 q=LeaveRequest(company_id=cid,**x.model_dump());s.add(q);s.flush();audit(s,cid,u.id,'create','leave',q.id,x.model_dump(mode='json'));s.commit();return obj(q)

def approve_leave(lid: int, ctx, s: Session):
 return _decide(lid, ctx, s, 'approved')

def reject_leave(lid: int, ctx, s: Session):
 return _decide(lid, ctx, s, 'rejected')

def payroll_list(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(PayrollRun).where(PayrollRun.company_id==ctx[1]).order_by(PayrollRun.period.desc())).all()]

def payroll_get(rid: int, ctx, s: Session):
 return _run_dict(s, same_company(s, PayrollRun, rid, ctx[1]))

def payroll_create(x: PayrollRunIn, ctx, s: Session):
 """محاسبهٔ پیش‌نویس حقوق ماه (YYYY-MM): حقوق پایه + پاداش − کسر مرخصی بدون‌حقوق"""
 u,cid,r=ctx
 try: y,m=int(x.period[:4]),int(x.period[5:7]); first=date(y,m,1); assert x.period[4]=='-' and len(x.period)==7
 except Exception: raise HTTPException(400,'دوره باید به‌شکل YYYY-MM باشد')
 last=(date(y+(m==12),m%12+1,1)-timedelta(days=1))
 if s.scalar(select(PayrollRun.id).where(PayrollRun.company_id==cid,PayrollRun.period==x.period)): raise HTTPException(409,'برای این دوره قبلاً حقوق محاسبه شده است')
 emps=s.scalars(select(Employee).where(Employee.company_id==cid,Employee.active==True).order_by(Employee.id)).all()
 if not emps: raise HTTPException(400,'کارمند فعالی وجود ندارد')
 for eid,b in x.bonuses.items():
  if b<0 or not any(e.id==eid for e in emps): raise HTTPException(400,'پاداش نامعتبر یا کارمند ناشناس')
 run=PayrollRun(company_id=cid,period=x.period,created_by=u.id);s.add(run);s.flush();tb=tbo=td=tn=Decimal(0)
 for e in emps:
  base=D(e.salary).quantize(Q2);bonus=D(x.bonuses.get(e.id,0)).quantize(Q2);ud=_unpaid_days(s,e.id,first,last)
  ded=min(base,(base/DAYS_IN_MONTH*ud)).quantize(Q2);net=base+bonus-ded
  s.add(PayrollLine(run_id=run.id,employee_id=e.id,base=base,bonus=bonus,unpaid_days=ud,deduction=ded,net=net));tb+=base;tbo+=bonus;td+=ded;tn+=net
 run.total_base=tb;run.total_bonus=tbo;run.total_deduction=td;run.total_net=tn;s.flush();audit(s,cid,u.id,'create','payroll',run.id,{'period':x.period});s.commit();return _run_dict(s,run)

def payroll_post(rid: int, ctx, s: Session):
 u,cid,r=ctx;run=s.get(PayrollRun,rid,with_for_update=True)
 if not run or run.company_id!=cid: raise HTTPException(404,'لیست حقوق یافت نشد')
 if run.status!='draft': raise HTTPException(409,'این لیست قبلاً ثبت شده است')
 if D(run.total_net)<=0: raise HTTPException(400,'جمع حقوق خالص صفر است')
 post_entry(s,cid,u.id,f'حقوق و دستمزد {run.period}',[{'code':SAL_EXP,'debit':run.total_net},{'code':SAL_PAY,'credit':run.total_net}],source=('payroll',run.id))
 run.status='posted';audit(s,cid,u.id,'post','payroll',run.id,{});s.commit();return obj(run)

def payroll_pay(rid: int, ctx, s: Session):
 u,cid,r=ctx;run=s.get(PayrollRun,rid,with_for_update=True)
 if not run or run.company_id!=cid: raise HTTPException(404,'لیست حقوق یافت نشد')
 if run.status!='posted': raise HTTPException(409,'ابتدا لیست حقوق باید ثبت (سندزنی) شود' if run.status=='draft' else 'این لیست قبلاً پرداخت شده است')
 post_entry(s,cid,u.id,f'پرداخت حقوق {run.period}',[{'code':SAL_PAY,'debit':run.total_net},{'code':BANK,'credit':run.total_net}],source=('payroll_pay',run.id))
 run.status='paid';audit(s,cid,u.id,'pay','payroll',run.id,{});s.commit();return obj(run)

def payroll_delete(rid: int, ctx, s: Session):
 u,cid,r=ctx;run=same_company(s,PayrollRun,rid,cid)
 if run.status!='draft': raise HTTPException(409,'فقط پیش‌نویس قابل حذف است')
 for l in s.scalars(select(PayrollLine).where(PayrollLine.run_id==run.id)): s.delete(l)
 s.delete(run);audit(s,cid,u.id,'delete','payroll',rid,{});s.commit();return {'ok':True}


def payslip_data(rid: int, eid: int, ctx, s: Session):
 u,cid,r=ctx;run=same_company(s,PayrollRun,rid,cid);e=same_company(s,Employee,eid,cid)
 l=s.scalar(select(PayrollLine).where(PayrollLine.run_id==run.id,PayrollLine.employee_id==e.id))
 if not l: raise HTTPException(404,'فیش حقوقی این کارمند در این دوره یافت نشد')
 co=s.get(Company,cid)
 return {'company':{'name':co.name if co else ''},'period':run.period,'status':run.status,'employee':{'name':e.name,'position':e.position},'line':obj(l)}

def payslip_pdf(rid: int, eid: int, ctx, s: Session):
 from app.services.exporters import payslip_pdf as _render
 d=payslip_data(rid,eid,ctx,s)
 try: data=_render(d)
 except RuntimeError as ex: raise HTTPException(503,str(ex))
 audit(s,ctx[1],ctx[0].id,'payslip_pdf','payroll',rid,{'employee_id':eid});s.commit();return data,f"{d['period']}-{eid}"

def shifts(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(Shift).where(Shift.company_id==ctx[1]).order_by(Shift.id)).all()]

def add_shift(x: ShiftIn, ctx, s: Session):
 u,cid,r=ctx
 if s.scalar(select(Shift.id).where(Shift.company_id==cid,Shift.name==x.name)): raise HTTPException(409,'شیفت با این نام وجود دارد')
 if x.start_time==x.end_time: raise HTTPException(400,'شروع و پایان شیفت یکسان است')
 q=Shift(company_id=cid,**x.model_dump());s.add(q);s.flush();audit(s,cid,u.id,'create','shift',q.id,x.model_dump(mode='json'));s.commit();s.refresh(q);return obj(q)

def patch_shift(sid: int, x: ShiftPatch, ctx, s: Session):
 u,cid,r=ctx;q=same_company(s,Shift,sid,cid)
 for k,v in x.model_dump(exclude_unset=True).items():
  if v is not None: setattr(q,k,v)
 if q.start_time==q.end_time: raise HTTPException(400,'شروع و پایان شیفت یکسان است')
 audit(s,cid,u.id,'update','shift',q.id,x.model_dump(mode='json',exclude_unset=True));s.commit();s.refresh(q);return obj(q)

def assign_shift(eid: int, x: EmployeeShiftIn, ctx, s: Session):
 u,cid,r=ctx;e=same_company(s,Employee,eid,cid);es=s.scalar(select(EmployeeShift).where(EmployeeShift.employee_id==e.id))
 if x.shift_id is None:
  if es: s.delete(es)
  audit(s,cid,u.id,'unassign','employee_shift',e.id);s.commit();return {'employee_id':e.id,'shift_id':None}
 sh=same_company(s,Shift,x.shift_id,cid)
 if not sh.active: raise HTTPException(409,'شیفت غیرفعال است')
 if es: es.shift_id=sh.id
 else: s.add(EmployeeShift(company_id=cid,employee_id=e.id,shift_id=sh.id))
 audit(s,cid,u.id,'assign','employee_shift',e.id,{'shift_id':sh.id});s.commit();return {'employee_id':e.id,'shift_id':sh.id}

def attendance_report(period: str, ctx, s: Session):
 """گزارش ماهانهٔ حضور: روز حضور، تأخیر، تعجیل خروج، اضافه‌کاری (دقیقه) نسبت به شیفت تخصیص‌یافته؛ بدون شیفت فقط روز/ساعت کارکرد."""
 u,cid,r=ctx
 try: y,m=int(period[:4]),int(period[5:7]); assert period[4]=='-' and len(period)==7; first=date(y,m,1)
 except Exception: raise HTTPException(400,'دوره باید به‌شکل YYYY-MM باشد')
 last=date(y+(m==12),m%12+1,1)-timedelta(days=1)
 emps=s.scalars(select(Employee).where(Employee.company_id==cid,Employee.active==True).order_by(Employee.id)).all();out=[]
 sh={x.id:x for x in s.scalars(select(Shift).where(Shift.company_id==cid)).all()};asg={x.employee_id:x.shift_id for x in s.scalars(select(EmployeeShift).where(EmployeeShift.company_id==cid)).all()}
 for e in emps:
  rows=s.scalars(select(Attendance).where(Attendance.company_id==cid,Attendance.employee_id==e.id,Attendance.day>=first,Attendance.day<=last)).all()
  sf=sh.get(asg.get(e.id));t={'late':0,'early_leave':0,'overtime':0,'worked':0}
  for a in rows:
   if sf:
    mt=shift_metrics(a.day,a.check_in,a.check_out,sf.start_time,sf.end_time,sf.grace_minutes)
    for k in t: t[k]+=mt[k]
   elif a.check_out: t['worked']+=max(0,int((a.check_out-a.check_in).total_seconds()//60))
  out.append({'employee_id':e.id,'employee':e.name,'shift':sf.name if sf else '','days':len(rows),**{k+'_minutes':v for k,v in t.items()}})
 return {'period':period,'rows':out}
