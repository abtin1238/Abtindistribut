import os,uuid
from datetime import date,datetime,timedelta,timezone
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_field.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app);PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
def role_id(A,name):
 client.post('/api/roles/templates',headers=A);return next(r['id'] for r in client.get('/api/roles',headers=A).json() if r['name']==name)
def mkuser(A,role='بازاریاب'):
 u='f'+uuid.uuid4().hex[:8];r=client.post('/api/users',headers=A,json={'branch_id':1,'username':u,'password':PW,'name':u,'role_id':role_id(A,role),'company_ids':[]});assert r.status_code==200,r.text
 return login(u,PW),r.json()['id']
def cust(A,tag,**kw): return client.post('/api/customers',headers=A,json={'code':tag+uuid.uuid4().hex[:5],'name':tag,'credit_limit':10**9,**kw}).json()
def stocked(A,qty=50,price=100):
 sfx=uuid.uuid4().hex[:6];p=client.post('/api/products',headers=A,json={'sku':'P'+sfx,'name':'k'+sfx,'base_price':price}).json();w=client.get('/api/warehouses',headers=A).json()[0]
 client.post('/api/stock/adjust',headers=A,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':qty,'kind':'in'});return p,w
def sync(h,*ev): return client.post('/api/sync',headers=h,json={'events':list(ev)}).json()
UTCDAY=lambda:datetime.now(timezone.utc).date().isoformat()

def test_gps_status_and_radius_setting():
 A=login();V,_=mkuser(A);c=cust(A,'G1',lat=35.7,lng=51.4);nc=cust(A,'G2')
 near=client.post('/api/visits',headers=V,json={'customer_id':c['id'],'lat':35.7003,'lng':51.4}).json();assert near['gps_status']=='ok' and near['distance_m']<50
 far=client.post('/api/visits',headers=V,json={'customer_id':c['id'],'lat':35.75,'lng':51.4}).json();assert far['gps_status']=='out_of_range' and far['distance_m']>5000
 assert client.post('/api/visits',headers=V,json={'customer_id':c['id']}).json()['gps_status']=='no_visit_gps'
 assert client.post('/api/visits',headers=V,json={'customer_id':nc['id'],'lat':35.7,'lng':51.4}).json()['gps_status']=='no_customer_gps'
 assert client.post('/api/visits',headers=V,json={'customer_id':c['id'],'lat':95,'lng':0}).status_code==422
 assert client.put('/api/settings/visit',headers=V,json={'radius_m':10}).status_code==403
 assert client.put('/api/settings/visit',headers=A,json={'radius_m':10}).json()['radius_m']==10
 assert client.post('/api/visits',headers=V,json={'customer_id':c['id'],'lat':35.7003,'lng':51.4}).json()['gps_status']=='out_of_range'
 client.put('/api/settings/visit',headers=A,json={'radius_m':150})
 hist=client.get('/api/visits?gps_status=out_of_range',headers=A).json();assert hist and all(v['gps_status']=='out_of_range' for v in hist)
 assert all(v['user_id']!=0 for v in client.get('/api/visits',headers=V).json())

def test_finish_visit_result_rules_and_order_link():
 A=login();V,_=mkuser(A);c=cust(A,'F1');p,w=stocked(A)
 v=client.post('/api/visits',headers=V,json={'customer_id':c['id']}).json();u=f"/api/visits/{v['id']}/finish"
 assert client.post(u,headers=V,json={'result':'bogus'}).status_code==400
 assert client.post(u,headers=V,json={'result':'no_order'}).status_code==400
 o=client.post('/api/orders',headers=V,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}).json()
 r=client.post(u,headers=V,json={'result':'ordered','note':'ok'});assert r.status_code==200 and r.json()['order_id']==o['id'] and r.json()['ended_at']
 assert client.post(u,headers=V,json={'result':'follow_up'}).status_code==409
 assert client.post(u,headers=V).status_code==200   # بستن بدون بدنه idempotent
 v2=client.post('/api/visits',headers=V,json={'customer_id':c['id']}).json()
 r=client.post(f"/api/visits/{v2['id']}/finish",headers=V,json={'result':'no_order','no_order_reason':'موجودی کافی دارد'});assert r.json()['no_order_reason']=='موجودی کافی دارد'
 other=cust(A,'F2');o2=client.post('/api/orders',headers=A,json={'customer_id':other['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':1}]}).json()
 v3=client.post('/api/visits',headers=V,json={'customer_id':c['id']}).json()
 assert client.post(f"/api/visits/{v3['id']}/finish",headers=V,json={'result':'ordered','order_id':o2['id']}).status_code==404   # سفارش مشتری دیگر
 V2,_=mkuser(A);assert client.post(f"/api/visits/{v3['id']}/finish",headers=V2).status_code==403

def test_plan_completion_today_list_and_foreign_plan():
 A=login();V,uid=mkuser(A);V2,uid2=mkuser(A);c1=cust(A,'P1');c2=cust(A,'P2');day=UTCDAY()
 assert client.post('/api/visit-plans',headers=V,json={'user_id':uid2,'day':day,'customer_ids':[c1['id']]}).status_code==403
 plan=client.post('/api/visit-plans',headers=V,json={'user_id':uid,'day':day,'customer_ids':[c1['id'],c2['id']]}).json()
 assert client.post('/api/visit-plans',headers=V,json={'user_id':uid,'day':day,'customer_ids':[c1['id'],c1['id']]}).status_code==400
 tl=client.get('/api/visit-plans/today?day='+day,headers=V).json();assert [i['customer']['id'] for i in tl]==[c1['id'],c2['id']] and all(i['status']=='pending' for i in tl)
 assert client.get('/api/visit-plans/today?day='+day,headers=V2).json()==[]
 assert client.post('/api/visits',headers=V2,json={'customer_id':c1['id'],'plan_id':plan['id']}).status_code==404
 client.post('/api/visits',headers=V,json={'customer_id':c1['id'],'plan_id':plan['id']})
 assert next(p for p in client.get('/api/visit-plans',headers=V).json() if p['id']==plan['id'])['status']=='planned'
 client.post('/api/visits',headers=V,json={'customer_id':c2['id'],'plan_id':plan['id']})
 assert next(p for p in client.get('/api/visit-plans',headers=V).json() if p['id']==plan['id'])['status']=='done'
 assert all(i['status']=='visited' for i in client.get('/api/visit-plans/today?day='+day,headers=V).json())

def test_route_suggestion_nearest_neighbor_and_exclusion():
 A=login();V,_=mkuser(A);reg='R'+uuid.uuid4().hex[:6]
 a=cust(A,'A',region=reg,lat=35.700,lng=51.400);b=cust(A,'B',region=reg,lat=35.701,lng=51.401);c=cust(A,'C',region=reg,lat=35.800,lng=51.500);d=cust(A,'D',region=reg)
 r=client.get(f'/api/visit-plans/suggest?region={reg}&lat=35.8&lng=51.5&day={UTCDAY()}',headers=V).json()
 assert [x['id'] for x in r]==[c['id'],b['id'],a['id'],d['id']] and r[0]['distance_km']==0 and r[-1]['distance_km'] is None
 assert len(client.get(f'/api/visit-plans/suggest?region={reg}&limit=2&day={UTCDAY()}',headers=V).json())==2
 client.post('/api/visits',headers=V,json={'customer_id':a['id']})
 assert a['id'] not in [x['id'] for x in client.get(f'/api/visit-plans/suggest?region={reg}&day={UTCDAY()}',headers=V).json()]
 assert client.get('/api/visit-plans/suggest?lat=999',headers=V).status_code==422

def test_lead_funnel_rules_and_scope():
 A=login();S,_=mkuser(A,'فروشنده');S2,_=mkuser(A,'فروشنده')
 l=client.post('/api/leads',headers=S,json={'title':'L1','value':1000,'source':'تلفنی'}).json();assert l['stage']=='new' and l['created_at']
 assert client.post('/api/leads',headers=S,json={'title':'x','stage':'won'}).status_code==400
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'won'}).status_code==409          # از new مستقیم برنده نمی‌شود
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'nope'}).status_code==400
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S2,json={'stage':'contacted'}).status_code==404   # مال دیگری
 tomorrow=(date.today()+timedelta(days=1)).isoformat()
 assert client.post(f"/api/leads/{l['id']}/activities",headers=S,json={'kind':'call','note':'تماس','next_followup':'2000-01-01'}).status_code==400
 r=client.post(f"/api/leads/{l['id']}/activities",headers=S,json={'kind':'call','note':'تماس','next_followup':tomorrow}).json();assert r['stage']=='contacted' and r['next_followup']==tomorrow
 assert client.post(f"/api/leads/{l['id']}/activities",headers=S,json={'kind':'bad'}).status_code==400
 assert l['id'] in [x['id'] for x in client.get('/api/leads/followups?days=1',headers=S).json()] and l['id'] not in [x['id'] for x in client.get('/api/leads/followups?days=0',headers=S).json()]
 hist=client.get(f"/api/leads/{l['id']}/activities",headers=S).json();assert {h['kind'] for h in hist}>={'call','stage'}
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'lost'}).status_code==400          # دلیل لازم است
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'qualified'}).status_code==200
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'lost','lost_reason':'قیمت'}).json()['closed_at']
 assert client.patch(f"/api/leads/{l['id']}/stage",headers=S,json={'stage':'new'}).status_code==409           # بسته‌شده
 assert l['id'] not in [x['id'] for x in client.get('/api/leads',headers=S2).json()] and l['id'] in [x['id'] for x in client.get('/api/leads',headers=A).json()]

def test_tasks_and_call_reminders():
 A=login();S,sid=mkuser(A,'فروشنده');S2,_=mkuser(A,'فروشنده');today=date.today().isoformat()
 t=client.post('/api/tasks',headers=S,json={'title':'تماس با آقای الف','kind':'call','due_date':today}).json();assert t['status']=='open' and t['assignee_id']==sid
 t2=client.post('/api/tasks',headers=S,json={'title':'بعداً','due_date':(date.today()+timedelta(days=20)).isoformat()}).json()
 assert client.post('/api/tasks',headers=S,json={'title':'x','assignee_id':1}).status_code==403
 assert client.post('/api/tasks',headers=S,json={'title':'x','kind':'zzz'}).status_code==400
 rm=client.get('/api/tasks/reminders',headers=S).json();assert [x['id'] for x in rm['calls']]==[t['id']] and t2['id'] not in [x['id'] for x in rm['tasks']]
 assert client.get('/api/tasks/reminders',headers=S2).json()['calls']==[]
 assert client.patch(f"/api/tasks/{t['id']}",headers=S2,json={'status':'done'}).status_code==404
 assert client.patch(f"/api/tasks/{t['id']}",headers=S,json={'status':'done'}).json()['done_at']
 assert client.patch(f"/api/tasks/{t['id']}",headers=S,json={'status':'done'}).status_code==409
 assert client.get('/api/tasks/reminders',headers=S).json()['calls']==[]
 assigned=client.post('/api/tasks',headers=A,json={'title':'برای فروشنده','assignee_id':sid}).json();assert assigned['assignee_id']==sid
 assert any(n['title']=='وظیفه‌ی جدید' for n in client.get('/api/notifications',headers=S).json())

def test_proposal_server_pricing_flow_and_lead_won():
 A=login();S,_=mkuser(A,'فروشنده');c=cust(A,'PR');p,w=stocked(A,qty=10,price=250)
 l=client.post('/api/leads',headers=S,json={'title':'PL','customer_id':c['id']}).json()
 pr=client.post('/api/proposals',headers=S,json={'customer_id':c['id'],'lead_id':l['id'],'items':[{'product_id':p['id'],'quantity':4,'unit_price':1}]}).json()
 assert pr['status']=='draft' and float(pr['total'])==1000 and float(pr['lines'][0]['unit_price'])==250     # قیمت کلاینت نادیده گرفته می‌شود
 assert client.post(f"/api/proposals/{pr['id']}/accept",headers=S,json={'warehouse_id':w['id']}).status_code==409   # هنوز ارسال نشده
 assert client.post(f"/api/proposals/{pr['id']}/send",headers=S).json()['status']=='sent'
 assert next(x for x in client.get('/api/leads',headers=S).json() if x['id']==l['id'])['stage']=='proposal'
 assert client.post(f"/api/proposals/{pr['id']}/send",headers=S).status_code==409
 S2,_=mkuser(A,'فروشنده');assert client.get(f"/api/proposals/{pr['id']}",headers=S2).status_code==404
 r=client.post(f"/api/proposals/{pr['id']}/accept",headers=S,json={'warehouse_id':w['id']});assert r.status_code==200,r.text
 assert r.json()['status']=='accepted' and r.json()['order']['id']==r.json()['order_id'] and float(r.json()['order']['total'])==1000
 assert next(x for x in client.get('/api/leads',headers=S).json() if x['id']==l['id'])['stage']=='won'
 assert client.post(f"/api/proposals/{pr['id']}/accept",headers=S,json={'warehouse_id':w['id']}).status_code==409
 big=client.post('/api/proposals',headers=S,json={'customer_id':c['id'],'items':[{'product_id':p['id'],'quantity':500}]}).json();client.post(f"/api/proposals/{big['id']}/send",headers=S)
 assert client.post(f"/api/proposals/{big['id']}/accept",headers=S,json={'warehouse_id':w['id']}).status_code==400    # موجودی کافی نیست
 assert client.get(f"/api/proposals/{big['id']}",headers=S).json()['status']=='sent' and client.post(f"/api/proposals/{big['id']}/reject",headers=A).json()['status']=='rejected'   # رد پیشنهاد نیاز به automation.approve دارد (نقش فروشنده ندارد)
 assert client.post('/api/proposals',headers=S,json={'customer_id':c['id'],'valid_until':'2000-01-01','items':[{'product_id':p['id'],'quantity':1}]}).status_code==400
 assert client.post('/api/proposals',headers=S,json={'customer_id':c['id'],'items':[]}).status_code==422

def test_target_commission_from_real_invoices():
 A=login();V,vid=mkuser(A);V2,_=mkuser(A);c=cust(A,'T1');p,w=stocked(A,qty=100,price=200);period=datetime.now(timezone.utc).strftime('%Y-%m')
 assert client.put('/api/targets',headers=V,json={'user_id':vid,'period':period,'sales_target':1000,'commission_percent':5}).status_code==403
 assert client.put('/api/targets',headers=A,json={'user_id':vid,'period':'2026-13','sales_target':1}).status_code==422
 t=client.put('/api/targets',headers=A,json={'user_id':vid,'period':period,'sales_target':1000,'commission_percent':5});assert t.status_code==200,t.text
 assert client.put('/api/targets',headers=A,json={'user_id':vid,'period':period,'sales_target':2000,'commission_percent':5}).json()['id']==t.json()['id']   # upsert
 assert client.get('/api/targets/performance?period='+period,headers=V).json()[0]['actual'] in (0,'0','0.00',0.0) or float(client.get('/api/targets/performance?period='+period,headers=V).json()[0]['actual'])==0
 o=client.post('/api/orders',headers=V,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':5}]}).json()
 assert float(client.get('/api/targets/performance?period='+period,headers=V).json()[0]['actual'])==0            # قبل از تأیید فاکتوری نیست
 assert client.post(f"/api/orders/{o['id']}/approve",headers=A).status_code==200
 inv=next(i for i in client.get('/api/invoices',headers=A).json() if i['order_id']==o['id'])
 perf=client.get('/api/targets/performance?period='+period,headers=V).json()[0]
 assert float(perf['actual'])==float(inv['total']) and float(perf['commission'])==round(float(inv['total'])*0.05,2) and float(perf['attainment_percent'])==round(float(inv['total'])*100/2000,2) and perf['orders']>=1
 assert client.get('/api/targets/performance?period='+period,headers=V2).json()==[]
 assert any(x['user_id']==vid for x in client.get('/api/targets/performance?period='+period,headers=A).json())
 assert client.get('/api/targets/performance?period=bad',headers=A).status_code==400

def test_funnel_analytics_counts():
 A=login();S,sid=mkuser(A);c=cust(A,'FN')
 ids=[client.post('/api/leads',headers=S,json={'title':f'F{i}','value':100}).json()['id'] for i in range(4)]
 for i in ids[:2]: client.patch(f'/api/leads/{i}/stage',headers=S,json={'stage':'qualified'});client.patch(f'/api/leads/{i}/stage',headers=S,json={'stage':'won'})
 client.patch(f'/api/leads/{ids[2]}/stage',headers=S,json={'stage':'lost','lost_reason':'قیمت'})
 v=client.post('/api/visits',headers=S,json={'customer_id':c['id']}).json();client.post(f"/api/visits/{v['id']}/finish",headers=S,json={'result':'no_order','no_order_reason':'موجودی دارد'})
 f=client.get('/api/automation/funnel',headers=S).json();L=f['leads']
 assert L['total']==4 and L['won']==2 and L['lost']==1 and L['open']==1 and L['win_rate']==round(2/3,4) and L['created_to_won']==0.5 and L['lost_reasons']=={'قیمت':1} and float(L['won_value'])==200
 assert f['visits']['total']==1 and f['visits']['no_order_reasons']=={'موجودی دارد':1} and f['visits']['order_rate']==0
 assert client.get('/api/automation/funnel?start=2000-01-01&end=2000-01-02',headers=S).json()['leads']['total']==0

def test_sync_lead_task_and_visit_result_events():
 A=login();V,_=mkuser(A);c=cust(A,'SY');u=uuid.uuid4().hex[:6]
 r=sync(V,{'id':'ls'+u,'type':'lead.create','payload':{'title':'آفلاین'}},{'id':'la'+u,'type':'lead.activity','ref':'ls'+u,'payload':{'kind':'call','note':'x'}},
  {'id':'tc'+u,'type':'task.create','payload':{'title':'t','kind':'call'}},{'id':'td'+u,'type':'task.done','ref':'tc'+u},
  {'id':'vs'+u,'type':'visit.start','payload':{'customer_id':c['id'],'lat':35.7,'lng':51.4}},{'id':'vf'+u,'type':'visit.finish','ref':'vs'+u,'payload':{'result':'no_order','no_order_reason':'آفلاین','ended_at':'2026-10-01T08:30:00Z'}})
 assert [x['status'] for x in r['results']]==['applied']*6,r
 assert any(x['title']=='آفلاین' and x['stage']=='contacted' for x in client.get('/api/leads',headers=V).json())
 assert client.get('/api/tasks?status=done',headers=V).json()
 v=next(x for x in client.get('/api/visits',headers=V).json() if x['customer_id']==c['id']);assert v['result']=='no_order' and v['no_order_reason']=='آفلاین'
 bad=sync(V,{'id':'vb'+u,'type':'visit.start','payload':{'customer_id':c['id']}},{'id':'vbf'+u,'type':'visit.finish','ref':'vb'+u,'payload':{'result':'no_order'}})
 assert [x['status'] for x in bad['results']]==['applied','rejected']                 # بدون دلیل رد می‌شود، نه ذخیره‌ی خام
 assert sync(V,{'id':'ls'+u,'type':'lead.create','payload':{'title':'تکراری'}})['results'][0]['status']=='duplicate'
 A2,_=mkuser(A,'مأمور پخش');assert sync(A2,{'id':'x'+u,'type':'lead.create','payload':{'title':'n'}})['results'][0]['status']=='rejected'    # بدون automation.write
