"""تست‌های property-based (hypothesis): تعادل اسناد، تسهیم هزینه، میانگین موزون، Geofence، شیفت."""
import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from hypothesis import given, settings, strategies as st
from app.services.costing import allocate_freight, weighted_avg, weighted_avg_out
from app.services.geo import evaluate_geofences
from app.services.shifts import shift_metrics

money=st.decimals(min_value=0,max_value=10**9,places=2)
pos=st.decimals(min_value=Decimal('0.001'),max_value=10**6,places=3)

@given(nets=st.lists(money,min_size=1,max_size=30),freight=money)
def test_allocate_freight_sums_exactly(nets,freight):
 out=allocate_freight(nets,[Decimal(1)]*len(nets),freight)
 assert len(out)==len(nets) and sum(out,Decimal(0))==freight
 assert all(x>=0 for x in out[:-1])

@given(have=st.decimals(min_value=1,max_value=10**5,places=3),avg=st.decimals(min_value=0,max_value=10**6,places=4),q=st.decimals(min_value=Decimal('0.001'),max_value=10**3,places=3),u=st.decimals(min_value=0,max_value=10**6,places=4))
def test_weighted_avg_between_bounds_and_return_restores(have,avg,q,u):
 n=weighted_avg(have,avg,q,u); eps=Decimal('0.0001')
 assert min(avg,u)-eps<=n<=max(avg,u)+eps
 back=weighted_avg_out(have+q,n,q,u)
 assert abs(back-avg)<=Decimal('0.00005')*(have+q)/have+eps

@given(st.lists(st.tuples(st.floats(35.69,35.71),st.floats(51.39,51.41)),min_size=1,max_size=60))
def test_geofence_events_alternate_starting_with_enter(coords):
 t0=datetime(2026,3,2,6,0);pts=[{'lat':a,'lng':b,'t':t0+timedelta(minutes=i)} for i,(a,b) in enumerate(coords)]
 ev,inside=evaluate_geofences(pts,[{'id':1,'lat':35.70,'lng':51.40,'radius_m':500}],set())
 kinds=[e['kind'] for e in ev]
 assert all(k==('enter' if i%2==0 else 'exit') for i,k in enumerate(kinds))
 assert (1 in inside)==(len(kinds)%2==1)

@given(h=st.integers(0,23),m=st.integers(0,59),dur=st.integers(0,16*60),sh=st.integers(5,10),eh=st.integers(14,22),grace=st.integers(0,60))
def test_shift_metrics_non_negative_and_exclusive(h,m,dur,sh,eh,grace):
 tz=ZoneInfo('Asia/Tehran');cin=datetime(2026,3,2,h,m);r=shift_metrics(date(2026,3,2),cin,cin+timedelta(minutes=dur),time(sh,0),time(eh,0),grace,tz)
 assert all(v>=0 for v in r.values()) and not (r['early_leave']>0 and r['overtime']>0) and r['worked']==dur

# --- API: تعادل دفتر (نیازمند fastapi) ---
def _client():
 os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_prop.sqlite3'); os.environ['ADMIN_PASSWORD']='test-password'
 from fastapi.testclient import TestClient
 from app.main import app
 c=TestClient(app); r=c.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return c,{'Authorization':'Bearer '+r.json()['token']}
CODES=['1110','1120','4110','4120']

@settings(max_examples=25,deadline=None)
@given(debits=st.lists(st.integers(1,10**7),min_size=1,max_size=4),split=st.integers(1,4),skew=st.integers(0,1))
def test_posted_entries_keep_trial_balance_balanced(debits,split,skew):
 c,h=_client();total=sum(debits)
 cr=[total//split]*split;cr[-1]+=total-sum(cr)
 lines=[{'account_code':CODES[i%4],'debit':d} for i,d in enumerate(debits)]+[{'account_code':CODES[(i+1)%4],'credit':x} for i,x in enumerate(cr)]
 if skew: lines[0]['debit']+=1   # نامتوازن ← باید رد شود
 r=c.post('/api/journal',headers=h,json={'description':'prop','lines':lines})
 assert (r.status_code==400) if skew else (r.status_code==200),r.text
 tb=c.get('/api/reports/trial-balance',headers=h).json(); assert tb['balanced'] is True
