import os,uuid,random
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_s20bank.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from datetime import date,timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def iban():
 b='%022d'%random.randrange(10**22); return f'IR{98-int(b+"182700")%97:02d}{b}'
def acc(h,opening=0,**kw):
 r=client.post('/api/bank-accounts',headers=h,json={'name':'B'+uuid.uuid4().hex[:6],'bank_name':'ملی','opening_balance':opening,**kw}); assert r.status_code==200,r.text; return r.json()
def bal(h,aid): return Decimal(str(next(x for x in client.get('/api/bank-accounts',headers=h).json() if x['id']==aid)['balance']))
def chk(h,**kw):
 body={'number':uuid.uuid4().hex[:8],'kind':'received','amount':100,'due_date':str(date.today()),**kw}
 return client.post('/api/checks',headers=h,json=body)

def test_iban_helper_matches_server_rule():
 from app.modules.banking import valid_iban
 assert valid_iban(iban()) and not valid_iban('IR'+'1'*24) and not valid_iban('IR12')

def test_account_opening_balance_and_validation():
 h=H(); a=acc(h,opening=1000,iban=iban()); assert a['ledger_code'].startswith('1120') and Decimal(str(a['balance']))==Decimal(1000)
 assert client.post('/api/bank-accounts',headers=h,json={'name':a['name']}).status_code==409
 assert client.post('/api/bank-accounts',headers=h,json={'name':'X'+uuid.uuid4().hex[:5],'iban':'IR123'}).status_code==400
 tb=client.get('/api/reports/trial-balance',headers=h).json(); assert tb['balanced'] and any(r['code']==a['ledger_code'] for r in tb['rows'])
 st=client.get(f"/api/bank-accounts/{a['id']}/statement",headers=h).json(); assert len(st['rows'])==1 and Decimal(str(st['closing']))==Decimal(1000)
 assert client.patch(f"/api/bank-accounts/{a['id']}",headers=h,json={'active':False}).status_code==409  # مانده غیرصفر

def test_cleared_checks_move_the_specific_account():
 h=H(); a=acc(h,opening=500); aid=a['id']
 rc=chk(h,kind='received',amount=200).json()
 assert client.patch(f"/api/checks/{rc['id']}",headers=h,json={'status':'deposited','bank_account_id':aid}).status_code==200
 assert bal(h,aid)==Decimal(500)  # ایداع هنوز سند مالی ندارد
 assert client.patch(f"/api/checks/{rc['id']}",headers=h,json={'status':'cleared'}).status_code==200
 assert bal(h,aid)==Decimal(700)
 ic=chk(h,kind='issued',amount=150,bank_account_id=aid).json(); assert ic['bank']=='ملی'
 oa=next(x for x in client.get('/api/bank-accounts',headers=h).json() if x['id']==aid); assert Decimal(str(oa['open_issued']))==Decimal(150)
 assert client.patch(f"/api/checks/{ic['id']}",headers=h,json={'status':'cleared'}).status_code==200
 assert bal(h,aid)==Decimal(550)
 hist=client.get(f"/api/checks/{rc['id']}/history",headers=h).json(); assert [x['action'] for x in hist]==['created','status','status'] and hist[-1]['to_status']=='cleared'
 other=acc(h); r2=chk(h,kind='received',amount=10).json()
 assert client.patch(f"/api/checks/{r2['id']}",headers=h,json={'status':'deposited','bank_account_id':aid}).status_code==200
 assert client.patch(f"/api/checks/{r2['id']}",headers=h,json={'status':'cleared','bank_account_id':other['id']}).status_code==409  # به حساب دیگری قابل‌جابه‌جایی نیست
 assert client.patch(f"/api/checks/{r2['id']}",headers=h,json={'status':'bounced','bank_account_id':aid}).status_code==400  # حساب فقط هنگام ایداع/وصول

def test_received_check_cannot_pick_account_or_book_at_creation():
 h=H(); a=acc(h); assert chk(h,kind='received',bank_account_id=a['id']).status_code==400
 assert chk(h,number='').status_code==400  # بدون دسته‌چک شماره الزامی است

def test_chequebook_leaf_rules():
 h=H(); a=acc(h); aid=a['id']; s=random.randrange(1000,900000)
 cb=client.post('/api/chequebooks',headers=h,json={'bank_account_id':aid,'series':'S','start_no':s,'end_no':s+2}); assert cb.status_code==200,cb.text; cb=cb.json(); assert cb['remaining']==3 and cb['next_no']==s
 assert client.post('/api/chequebooks',headers=h,json={'bank_account_id':aid,'series':'S','start_no':s+1,'end_no':s+5}).status_code==409
 assert client.post('/api/chequebooks',headers=h,json={'bank_account_id':aid,'start_no':5,'end_no':1}).status_code==400
 c1=chk(h,kind='issued',number='',chequebook_id=cb['id']); assert c1.status_code==200 and c1.json()['number']==str(s) and c1.json()['bank_account_id']==aid
 assert chk(h,kind='issued',number=str(s),chequebook_id=cb['id']).status_code==409
 assert chk(h,kind='issued',number=str(s+99),chequebook_id=cb['id']).status_code==400
 assert chk(h,kind='received',chequebook_id=cb['id']).status_code==400
 other=acc(h); assert chk(h,kind='issued',chequebook_id=cb['id'],bank_account_id=other['id']).status_code==400
 v=client.post(f"/api/chequebooks/{cb['id']}/void-leaf",headers=h,json={'number':str(s+1),'note':'خراب'}); assert v.status_code==200 and v.json()['remaining']==1
 lv={x['number']:x['state'] for x in client.get(f"/api/chequebooks/{cb['id']}/leaves",headers=h).json()['leaves']}; assert lv=={str(s):'used',str(s+1):'void',str(s+2):'unused'}
 assert bal(h,aid)==Decimal(0)  # برگ باطل سند مالی ندارد
 c3=chk(h,kind='issued',number='',chequebook_id=cb['id']); assert c3.status_code==200 and c3.json()['number']==str(s+2)
 fin=next(x for x in client.get('/api/chequebooks',headers=h).json() if x['id']==cb['id']); assert fin['status']=='finished' and fin['remaining']==0
 assert chk(h,kind='issued',number='',chequebook_id=cb['id']).status_code==409

def test_cancelled_chequebook_blocks_new_checks():
 h=H(); a=acc(h); s=random.randrange(1000,900000)
 cb=client.post('/api/chequebooks',headers=h,json={'bank_account_id':a['id'],'start_no':s,'end_no':s+4}).json()
 assert client.patch(f"/api/chequebooks/{cb['id']}",headers=h,json={'status':'cancelled'}).status_code==200
 assert chk(h,kind='issued',number='',chequebook_id=cb['id']).status_code==409
 assert client.patch(f"/api/chequebooks/{cb['id']}",headers=h,json={'status':'finished'}).status_code==400

def test_transfers():
 h=H(); a=acc(h,opening=300); b=acc(h)
 assert client.post('/api/bank-transfers',headers=h,json={'from_account_id':a['id'],'to_account_id':b['id'],'amount':100}).status_code==200
 assert bal(h,a['id'])==Decimal(200) and bal(h,b['id'])==Decimal(100)
 assert client.post('/api/bank-transfers',headers=h,json={'from_account_id':a['id'],'to_account_id':b['id'],'amount':999}).status_code==409
 assert client.post('/api/bank-transfers',headers=h,json={'from_account_id':a['id'],'to_account_id':a['id'],'amount':1}).status_code==400
 assert client.post('/api/bank-transfers',headers=h,json={'amount':1}).status_code==400
 assert client.post('/api/bank-transfers',headers=h,json={'to_account_id':b['id'],'amount':50}).status_code==200  # صندوق → بانک
 assert bal(h,b['id'])==Decimal(150)
 assert client.post('/api/bank-transfers',headers=h,json={'from_account_id':b['id'],'amount':150}).status_code==200  # بانک → صندوق
 assert bal(h,b['id'])==Decimal(0)

def test_bank_payment_goes_to_chosen_account():
 h=H(); a=acc(h); cid=client.post('/api/customers',headers=h,json={'code':'BK'+uuid.uuid4().hex[:6],'name':'مشتری بانک'}).json()['id']
 r=client.post('/api/payments',headers=h,json={'customer_id':cid,'amount':75,'kind':'receipt','method':'transfer','bank_account_id':a['id']}); assert r.status_code==200,r.text
 assert bal(h,a['id'])==Decimal(75)
 assert client.post('/api/payments',headers=h,json={'customer_id':cid,'amount':5,'kind':'receipt','method':'cash','bank_account_id':a['id']}).status_code==400
 assert client.post('/api/payments',headers=h,json={'customer_id':cid,'amount':5,'kind':'receipt','method':'transfer','bank_account_id':999999}).status_code==404

def test_due_checks_report():
 h=H(); soon=chk(h,kind='issued',amount=10,due_date=str(date.today()+timedelta(days=3))).json(); late=chk(h,kind='received',amount=20,due_date=str(date.today()-timedelta(days=2))).json()
 far=chk(h,kind='issued',amount=30,due_date=str(date.today()+timedelta(days=200))).json()
 d=client.get('/api/checks/due?days=7',headers=h).json(); ids={x['id']:x for x in d['rows']}
 assert soon['id'] in ids and late['id'] in ids and far['id'] not in ids and ids[late['id']]['overdue'] and d['overdue_count']>=1
 assert client.get('/api/checks/due?days=-1',headers=h).status_code==422

def test_dashboard_bank_total_includes_accounts():
 h=H(); b=client.get('/api/ceo/summary',headers=h); assert b.status_code==200,b.text
 acc(h,opening=12345); a=client.get('/api/ceo/summary',headers=h); assert a.status_code==200
 assert Decimal(str(a.json()['kpis']['cash']['bank']))-Decimal(str(b.json()['kpis']['cash']['bank']))==Decimal(12345)
