import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from app.services.shifts import shift_metrics
TZ=ZoneInfo('Asia/Tehran')
def utc(h,m): return datetime(2026,3,2,h,m)   # Asia/Tehran = UTC+3:30 (بدون DST از ۲۰۲۲)
D=date(2026,3,2)

def test_on_time_within_grace_and_overtime():
 r=shift_metrics(D,utc(4,40),utc(14,0),time(8,0),time(17,0),15,TZ)   # ورود ۰۸:۱۰ محلی، خروج ۱۷:۳۰
 assert r['late']==0 and r['overtime']==30 and r['early_leave']==0 and r['worked']==560

def test_late_counts_from_shift_start_and_early_leave():
 r=shift_metrics(D,utc(4,50),utc(12,0),time(8,0),time(17,0),15,TZ)   # ۰۸:۲۰ تا ۱۵:۳۰
 assert r['late']==20 and r['early_leave']==90 and r['overtime']==0

def test_night_shift_end_next_day():
 r=shift_metrics(D,utc(18,30),datetime(2026,3,3,3,0),time(22,0),time(6,0),0,TZ)   # ۲۲:۰۰ تا ۰۶:۳۰ روز بعد
 assert r['late']==0 and r['overtime']==30 and r['early_leave']==0

def test_missing_checkout_only_late():
 r=shift_metrics(D,utc(5,0),None,time(8,0),time(17,0),0,TZ)
 assert r['late']==30 and r['worked']==0 and r['overtime']==0

# --- API (نیازمند fastapi) ---
def _client():
 os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_shift.sqlite3'); os.environ['ADMIN_PASSWORD']='test-password'
 from fastapi.testclient import TestClient
 from app.main import app
 c=TestClient(app); r=c.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return c,{'Authorization':'Bearer '+r.json()['token']}

def test_shift_crud_assign_and_report():
 c,h=_client()
 s=c.post('/api/shifts',headers=h,json={'name':'صبح-T','start_time':'08:00','end_time':'17:00','grace_minutes':10}); assert s.status_code==200,s.text
 assert c.post('/api/shifts',headers=h,json={'name':'صبح-T','start_time':'08:00','end_time':'17:00'}).status_code==409
 assert c.post('/api/shifts',headers=h,json={'name':'bad','start_time':'08:00','end_time':'08:00'}).status_code==400
 e=c.post('/api/employees',headers=h,json={'name':'E-shift','salary':1000}).json()['id']
 assert c.put(f'/api/employees/{e}/shift',headers=h,json={'shift_id':s.json()['id']}).status_code==200
 assert c.put(f'/api/employees/{e}/shift',headers=h,json={'shift_id':999999}).status_code==404
 c.post(f'/api/attendance/check-in?employee_id={e}',headers=h)
 rep=c.get(f'/api/attendance/report?period={__import__("datetime").date.today():%Y-%m}',headers=h); assert rep.status_code==200,rep.text
 row=next(x for x in rep.json()['rows'] if x['employee_id']==e); assert row['shift']=='صبح-T' and row['days']==1
 assert c.get('/api/attendance/report?period=2026-13x',headers=h).status_code==422
 assert c.patch(f'/api/shifts/{s.json()["id"]}',headers=h,json={'active':False}).json()['active'] is False
 assert c.put(f'/api/employees/{e}/shift',headers=h,json={'shift_id':s.json()["id"]}).status_code==409

def test_payslip_pdf_404_and_payload():
 c,h=_client()
 assert c.get('/api/payroll/runs/999999/payslip/1/pdf',headers=h).status_code==404
