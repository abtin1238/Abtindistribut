import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s19fiscal.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from datetime import date,timedelta
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def entry(h,amount=100):
 return client.post('/api/journal',headers=h,json={'description':'t','lines':[{'account_code':'1110','debit':amount,'credit':0},{'account_code':'3100','debit':0,'credit':amount}]})

def test_closed_period_blocks_posting_and_reopen_allows():
 h=H(); t=date.today()
 r=client.post('/api/fiscal/periods',headers=h,json={'name':'p','start_date':str(t-timedelta(days=5)),'end_date':str(t+timedelta(days=5))}); assert r.status_code==200,r.text
 pid=r.json()['id']
 assert entry(h).status_code==200
 assert client.post(f'/api/fiscal/periods/{pid}/close',headers=h).status_code==200
 assert client.post(f'/api/fiscal/periods/{pid}/close',headers=h).status_code==409
 assert entry(h).status_code==409
 assert client.post(f'/api/fiscal/periods/{pid}/reopen',headers=h).status_code==200
 assert entry(h).status_code==200

def test_overlap_and_bad_range_rejected():
 h=H(); t=date.today()
 assert client.post('/api/fiscal/periods',headers=h,json={'name':'o','start_date':str(t),'end_date':str(t+timedelta(days=1))}).status_code==409
 assert client.post('/api/fiscal/periods',headers=h,json={'name':'b','start_date':'2030-02-01','end_date':'2030-01-01'}).status_code==400
