from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.modules.hr.schemas import EmployeeShiftIn, ShiftIn, ShiftPatch
from app.schemas import EmployeeIn, LeaveIn, PayrollRunIn
from .service import employees as _s_employees, add_employee as _s_add_employee, attendance_in as _s_attendance_in, attendance_out as _s_attendance_out, attendance as _s_attendance, leaves as _s_leaves, add_leave as _s_add_leave, approve_leave as _s_approve_leave, reject_leave as _s_reject_leave, payroll_list as _s_payroll_list, payroll_get as _s_payroll_get, payroll_create as _s_payroll_create, payroll_post as _s_payroll_post, payroll_pay as _s_payroll_pay, payroll_delete as _s_payroll_delete

from . import service as _svc

router=APIRouter()

@router.get('/api/employees')
def employees(ctx=Depends(current), s: Session=Depends(db)):
 return _s_employees(ctx=ctx, s=s)

@router.post('/api/employees')
def add_employee(x: EmployeeIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_employee(x=x, ctx=ctx, s=s)

@router.post('/api/attendance/check-in')
def attendance_in(employee_id: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_attendance_in(employee_id=employee_id, ctx=ctx, s=s)

@router.post('/api/attendance/check-out')
def attendance_out(employee_id: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_attendance_out(employee_id=employee_id, ctx=ctx, s=s)

@router.get('/api/attendance')
def attendance(ctx=Depends(current), s: Session=Depends(db)):
 return _s_attendance(ctx=ctx, s=s)

@router.get('/api/leaves')
def leaves(ctx=Depends(current), s: Session=Depends(db)):
 return _s_leaves(ctx=ctx, s=s)

@router.post('/api/leaves')
def add_leave(x: LeaveIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_leave(x=x, ctx=ctx, s=s)

@router.post('/api/leaves/{lid}/approve')
def approve_leave(lid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_approve_leave(lid=lid, ctx=ctx, s=s)

@router.post('/api/leaves/{lid}/reject')
def reject_leave(lid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_reject_leave(lid=lid, ctx=ctx, s=s)

@router.get('/api/payroll/runs')
def payroll_list(ctx=Depends(current), s: Session=Depends(db)):
 return _s_payroll_list(ctx=ctx, s=s)

@router.get('/api/payroll/runs/{rid}')
def payroll_get(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_payroll_get(rid=rid, ctx=ctx, s=s)

@router.post('/api/payroll/runs')
def payroll_create(x: PayrollRunIn, ctx=Depends(current), s: Session=Depends(db)):
 'محاسبهٔ پیش\u200cنویس حقوق ماه (YYYY-MM): حقوق پایه + پاداش − کسر مرخصی بدون\u200cحقوق'
 return _s_payroll_create(x=x, ctx=ctx, s=s)

@router.post('/api/payroll/runs/{rid}/post')
def payroll_post(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_payroll_post(rid=rid, ctx=ctx, s=s)

@router.post('/api/payroll/runs/{rid}/pay')
def payroll_pay(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_payroll_pay(rid=rid, ctx=ctx, s=s)

@router.delete('/api/payroll/runs/{rid}')
def payroll_delete(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_payroll_delete(rid=rid, ctx=ctx, s=s)

@router.get('/api/payroll/runs/{rid}/payslip/{eid}/pdf')
def payslip_pdf(rid: int, eid: int, ctx=Depends(current), s: Session=Depends(db)):
 'فیش حقوقی PDF یک کارمند در یک دوره'
 data,name=_svc.payslip_pdf(rid=rid, eid=eid, ctx=ctx, s=s)
 return Response(content=data, media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="payslip-{name}.pdf"', 'Cache-Control': 'no-store'})

@router.get('/api/shifts')
def shifts(ctx=Depends(current), s: Session=Depends(db)):
 return _svc.shifts(ctx=ctx, s=s)

@router.post('/api/shifts')
def add_shift(x: ShiftIn, ctx=Depends(current), s: Session=Depends(db)):
 return _svc.add_shift(x=x, ctx=ctx, s=s)

@router.patch('/api/shifts/{sid}')
def patch_shift(sid: int, x: ShiftPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _svc.patch_shift(sid=sid, x=x, ctx=ctx, s=s)

@router.put('/api/employees/{eid}/shift')
def assign_shift(eid: int, x: EmployeeShiftIn, ctx=Depends(current), s: Session=Depends(db)):
 'تخصیص شیفت به کارمند (shift_id=null برای برداشتن)'
 return _svc.assign_shift(eid=eid, x=x, ctx=ctx, s=s)

@router.get('/api/attendance/report')
def attendance_report(period: str=Query(..., pattern=r'^\d{4}-\d{2}$'), ctx=Depends(current), s: Session=Depends(db)):
 'گزارش ماهانهٔ حضور: تأخیر/تعجیل/اضافه‌کاری نسبت به شیفت'
 return _svc.attendance_report(period=period, ctx=ctx, s=s)
