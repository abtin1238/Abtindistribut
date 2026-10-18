import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19hr.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

def test_leave_validation_and_decision():
 h=H(); eid=client.post('/api/employees',headers=h,json={'name':'E19','salary':3000}).json()['id']
 assert client.post('/api/leaves',headers=h,json={'employee_id':eid,'start_date':'2030-02-05','end_date':'2030-02-01'}).status_code==400
 assert client.post('/api/leaves',headers=h,json={'employee_id':eid,'kind':'x','start_date':'2030-02-01','end_date':'2030-02-02'}).status_code==400
 l=client.post('/api/leaves',headers=h,json={'employee_id':eid,'kind':'unpaid','start_date':'2030-02-01','end_date':'2030-02-03'}); assert l.status_code==200,l.text; lid=l.json()['id']
 assert client.post('/api/leaves',headers=h,json={'employee_id':eid,'start_date':'2030-02-03','end_date':'2030-02-04'}).status_code==409
 assert client.post(f'/api/leaves/{lid}/approve',headers=h).json()['status']=='approved'
 assert client.post(f'/api/leaves/{lid}/reject',headers=h).status_code==409

def test_payroll_calculation_posting_and_payment():
 h=H(); eid=client.post('/api/employees',headers=h,json={'name':'E19b','salary':3000}).json()['id']
 l=client.post('/api/leaves',headers=h,json={'employee_id':eid,'kind':'unpaid','start_date':'2031-02-01','end_date':'2031-02-03'}).json()['id']
 client.post(f'/api/leaves/{l}/approve',headers=h)
 assert client.post('/api/payroll/runs',headers=h,json={'period':'bad'}).status_code==400
 r=client.post('/api/payroll/runs',headers=h,json={'period':'2031-02','bonuses':{str(eid):200}}); assert r.status_code==200,r.text
 line=[x for x in r.json()['lines'] if x['employee_id']==eid][0]
 assert Decimal(str(line['deduction']))==Decimal('300.00') and Decimal(str(line['net']))==Decimal('2900.00') and line['unpaid_days'] in (3,3.0)
 rid=r.json()['id']
 assert client.post('/api/payroll/runs',headers=h,json={'period':'2031-02'}).status_code==409
 assert client.post(f'/api/payroll/runs/{rid}/pay',headers=h).status_code==409
 assert client.post(f'/api/payroll/runs/{rid}/post',headers=h).json()['status']=='posted'
 assert client.post(f'/api/payroll/runs/{rid}/post',headers=h).status_code==409
 assert client.delete(f'/api/payroll/runs/{rid}',headers=h).status_code==409
 assert client.post(f'/api/payroll/runs/{rid}/pay',headers=h).json()['status']=='paid'
