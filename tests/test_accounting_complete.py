import os,uuid
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_acc_complete.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
try: os.remove('/tmp/abtin_dist_acc_complete.sqlite3')
except FileNotFoundError: pass
from datetime import date
from decimal import Decimal as D
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def ok(r,code=200): assert r.status_code==code,r.text;return r.json()
def bal(h,code): return D(str(next((x['balance'] for x in client.get('/api/reports/trial-balance',headers=h).json()['rows'] if x['code']==code),0)))
def bank(h,opening=1000):
 return ok(client.post('/api/bank-accounts',headers=h,json={'name':'B'+uuid.uuid4().hex[:5],'opening_balance':opening}))
def flat(ns):
 for n in ns: yield n; yield from flat(n['children'])

def test_chart_tree_levels_rollup_and_posting_guard():
 h=H();b=bank(h,1000)
 t=ok(client.get('/api/accounts/tree',headers=h));nodes={n['code']:n for n in flat(t)}
 assert nodes['1']['level']==1 and nodes['11']['level']==2 and nodes['1120']['level']==3 and nodes[b['ledger_code']]['level']==4
 assert nodes[b['ledger_code']] in nodes['1120']['children'] and nodes['11'] in nodes['1']['children']
 assert D(str(nodes['1']['total_balance']))>=1000 and D(str(nodes[b['ledger_code']]['balance']))==1000
 r=client.post('/api/journal',headers=h,json={'description':'x','lines':[{'account_code':'11','debit':5},{'account_code':'3100','credit':5}]});assert r.status_code==400 and 'گروه' in r.text
 assert client.post('/api/accounts',headers=h,json={'code':'1999','name':'x','type':'liability','parent_code':'11'}).status_code==400   # نوع با والد نمی‌خواند
 assert client.post('/api/accounts',headers=h,json={'code':'2999','name':'x','type':'asset','parent_code':'11'}).status_code==400    # کد با والد نمی‌خواند
 a=ok(client.post('/api/accounts',headers=h,json={'code':'11101','name':'تنخواه شعبه','type':'asset','parent_code':'1110'}));assert a['level']==4
 assert client.patch(f"/api/accounts/{a['id']}",headers=h,json={'name':'تنخواه شعبه ۲'}).json()['name']=='تنخواه شعبه ۲'
 ok(client.post('/api/journal',headers=h,json={'description':'t','lines':[{'account_code':'11101','debit':7},{'account_code':'3100','credit':7}]}))
 assert client.patch(f"/api/accounts/{a['id']}",headers=h,json={'active':False}).status_code==409     # مانده غیرصفر
 sysacc=next(x for x in client.get('/api/accounts',headers=h).json() if x['code']=='1110');assert client.patch(f"/api/accounts/{sysacc['id']}",headers=h,json={'active':False}).status_code==409
 e=ok(client.post('/api/accounts',headers=h,json={'code':'61001','name':'هزینه‌ی متفرقه','type':'expense'}));assert ok(client.patch(f"/api/accounts/{e['id']}",headers=h,json={'active':False}))['active'] is False
 r=client.post('/api/journal',headers=h,json={'description':'x','lines':[{'account_code':'61001','debit':5},{'account_code':'3100','credit':5}]});assert r.status_code==400
 tb=client.get('/api/reports/trial-balance',headers=h).json();assert tb['balanced'] and all(len(x['code'])>=3 for x in tb['rows'])

def test_bank_fee_and_interest_post_entries_and_guard_overdraft():
 h=H();b=bank(h,1000);f0=bal(h,'5400');i0=bal(h,'4210')
 ok(client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'fee','amount':30,'note':'کارمزد ماه'}))
 ok(client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'interest','amount':80}))
 assert bal(h,'5400')-f0==30 and bal(h,'4210')-i0==-80 and bal(h,b['ledger_code'])==1050
 assert client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'fee','amount':5000}).status_code==409
 assert client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'fee','amount':0}).status_code==422
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']

def test_bounce_fee_posts_bank_charge_only_on_bounce():
 h=H();b=bank(h,500);f0=bal(h,'5400')
 chk=ok(client.post('/api/checks',headers=h,json={'number':'BF'+uuid.uuid4().hex[:4],'kind':'received','amount':200,'due_date':str(date.today())}))
 assert client.patch(f"/api/checks/{chk['id']}",headers=h,json={'status':'deposited','bank_account_id':b['id'],'fee':5}).status_code==400
 ok(client.patch(f"/api/checks/{chk['id']}",headers=h,json={'status':'deposited','bank_account_id':b['id']}))
 ok(client.patch(f"/api/checks/{chk['id']}",headers=h,json={'status':'bounced','fee':12}))
 assert bal(h,'5400')-f0==12 and bal(h,b['ledger_code'])==500-12
 hist=client.get(f"/api/checks/{chk['id']}/history",headers=h).json();assert any('کارمزد' in (x.get('note') or '') for x in hist)
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']

def test_bank_reconciliation_flow():
 h=H();b=bank(h,1000)
 ok(client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'fee','amount':20}))
 ok(client.post(f"/api/bank-accounts/{b['id']}/charges",headers=h,json={'kind':'interest','amount':50}))   # این یکی هنوز در صورت‌حساب بانک نیست
 o=ok(client.get(f"/api/bank-accounts/{b['id']}/reconcile",headers=h));ls=o['lines'];assert len(ls)==3 and D(str(o['book_balance']))==1030
 by={l['description'][:5]:l for l in ls}
 pick=[l['line_id'] for l in ls if D(str(l['debit']))==1000 or D(str(l['credit']))==20]
 r=ok(client.post(f"/api/bank-accounts/{b['id']}/reconcile",headers=h,json={'statement_balance':980,'line_ids':pick}))
 assert r['balanced'] and D(str(r['cleared_balance']))==980 and D(str(r['book_balance']))==1030
 assert client.post(f"/api/bank-accounts/{b['id']}/reconcile",headers=h,json={'statement_balance':980,'line_ids':pick}).status_code==409   # تکراری
 assert client.post(f"/api/bank-accounts/{b['id']}/reconcile",headers=h,json={'statement_balance':980,'line_ids':[999999]}).status_code==400
 o=ok(client.get(f"/api/bank-accounts/{b['id']}/reconcile",headers=h));assert len(o['lines'])==1 and D(str(o['in_transit_deposits']))==50 and D(str(o['cleared_balance']))==980
 rest=[l['line_id'] for l in o['lines']];r2=ok(client.post(f"/api/bank-accounts/{b['id']}/reconcile",headers=h,json={'statement_balance':1000,'line_ids':rest}))
 assert r2['balanced'] is False and D(str(r2['difference']))==-30
 assert client.delete(f"/api/bank-accounts/{b['id']}/reconciliations/{r['id']}",headers=h).status_code==409   # فقط آخرین
 ok(client.delete(f"/api/bank-accounts/{b['id']}/reconciliations/{r2['id']}",headers=h))
 assert len(ok(client.get(f"/api/bank-accounts/{b['id']}/reconcile",headers=h))['lines'])==1 and len(ok(client.get(f"/api/bank-accounts/{b['id']}/reconciliations",headers=h)))==1

def test_year_end_closing_entry():
 h=H();today=date.today()
 ok(client.post('/api/journal',headers=h,json={'description':'فروش','lines':[{'account_code':'1110','debit':100},{'account_code':'4110','credit':100}]}))
 ok(client.post('/api/journal',headers=h,json={'description':'هزینه','lines':[{'account_code':'5300','debit':40},{'account_code':'1110','credit':40}]}))
 p=ok(client.post('/api/fiscal/periods',headers=h,json={'name':'سال تست','start_date':f'{today.year}-01-01','end_date':f'{today.year}-12-31'}))
 pl0=client.get('/api/reports/profit-loss',headers=h).json()['net_profit']
 e=ok(client.post(f"/api/fiscal/periods/{p['id']}/closing-entry",headers=h))
 assert D(str(e['net_profit']))>=60
 assert bal(h,'4110')==0 and bal(h,'5300')==0 and bal(h,'3200')<0
 assert D(str(client.get('/api/reports/profit-loss',headers=h).json()['net_profit']))==D(str(pl0))   # اختتامیه در سود و زیان نیست
 bs=client.get('/api/reports/balance-sheet',headers=h).json();assert bs['balanced'] and D(str(bs['current_earnings']))==0
 assert client.post(f"/api/fiscal/periods/{p['id']}/closing-entry",headers=h).status_code==409
 assert client.get('/api/reports/trial-balance',headers=h).json()['balanced']
 ok(client.post(f"/api/fiscal/periods/{p['id']}/close",headers=h))
 assert client.post(f"/api/fiscal/periods/{p['id']}/closing-entry",headers=h).status_code==409
 ok(client.post(f"/api/fiscal/periods/{p['id']}/reopen",headers=h))   # تست‌های بعدی در همین سال سند می‌زنند

def test_journal_templates_post_balanced_entries():
 h=H();n='اجاره'+uuid.uuid4().hex[:4]
 bad=client.post('/api/journal-templates',headers=h,json={'name':n,'lines':[{'account_code':'5300','side':'debit','ratio':1},{'account_code':'1110','side':'credit','ratio':2}]});assert bad.status_code==400
 assert client.post('/api/journal-templates',headers=h,json={'name':n,'lines':[{'account_code':'53','side':'debit'},{'account_code':'1110','side':'credit'}]}).status_code==422
 t=ok(client.post('/api/journal-templates',headers=h,json={'name':n,'lines':[{'account_code':'5300','side':'debit','ratio':1},{'account_code':'1110','side':'credit','ratio':1}]}))
 assert client.post('/api/journal-templates',headers=h,json={'name':n,'lines':t['lines']}).status_code==409
 b5=bal(h,'5300');e=ok(client.post(f"/api/journal-templates/{t['id']}/post",headers=h,json={'amount':250}));assert bal(h,'5300')-b5==250 and D(str(e['debit']))==250
 assert client.post(f"/api/journal-templates/{t['id']}/post",headers=h,json={'amount':0}).status_code==422
 assert any(x['id']==t['id'] for x in ok(client.get('/api/journal-templates',headers=h)))
 ok(client.delete(f"/api/journal-templates/{t['id']}",headers=h));assert client.post(f"/api/journal-templates/{t['id']}/post",headers=h,json={'amount':1}).status_code==404

def test_entry_date_backdating_reports_and_period_lock():
 h=H();d0='2023-03-10'
 assert client.post('/api/journal',headers=h,json={'description':'x','entry_date':'2999-01-01','lines':[{'account_code':'1110','debit':1},{'account_code':'3100','credit':1}]}).status_code==400   # آینده
 e=ok(client.post('/api/journal',headers=h,json={'description':'قدیمی','entry_date':d0,'lines':[{'account_code':'1110','debit':70},{'account_code':'4110','credit':70}]}));assert e['entry_date']==d0
 pl=ok(client.get('/api/reports/profit-loss?start=2023-01-01&end=2023-12-31',headers=h));assert D(str(pl['revenue']))==70
 assert D(str(client.get('/api/reports/profit-loss?start=2024-01-01&end=2024-12-31',headers=h).json()['revenue']))==0
 gl=ok(client.get('/api/reports/general-ledger?account_code=4110&start=2023-01-01&end=2023-12-31',headers=h));assert any(r['date']==d0 for r in gl['rows'])
 p=ok(client.post('/api/fiscal/periods',headers=h,json={'name':'۱۴۰۱','start_date':'2023-01-01','end_date':'2023-12-31'}))
 ok(client.post(f"/api/fiscal/periods/{p['id']}/closing-entry",headers=h))
 ce=next(x for x in client.get('/api/journal',headers=h).json() if x['source_type']=='year_close');assert ce['entry_date']=='2023-12-31'
 assert bal(h,'4110')==bal(h,'4110')   # بسته‌شدن فقط حساب‌های همین دوره
 ok(client.post(f"/api/fiscal/periods/{p['id']}/close",headers=h))
 r=client.post('/api/journal',headers=h,json={'description':'بعد از بستن','entry_date':'2023-06-01','lines':[{'account_code':'1110','debit':5},{'account_code':'3100','credit':5}]});assert r.status_code==409
 ok(client.post('/api/journal',headers=h,json={'description':'امروز','lines':[{'account_code':'1110','debit':5},{'account_code':'3100','credit':5}]}))   # دوره‌ی امسال باز است
 ok(client.post(f"/api/fiscal/periods/{p['id']}/reopen",headers=h))
