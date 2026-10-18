from datetime import date
from app.services.geo import gps_check,haversine_m,suggest_route,valid_point
def test_haversine_known_distance():
 assert 110000<haversine_m(35.0,51.0,36.0,51.0)<112500
 assert haversine_m(35.7,51.4,35.7,51.4)==0
def test_gps_status_all_cases():
 assert gps_check(35.7,51.4,35.7005,51.4,150)[1]=='ok'
 d,st=gps_check(35.7,51.4,35.72,51.4,150);assert st=='out_of_range' and d>2000
 assert gps_check(None,None,35.7,51.4)==(None,'no_visit_gps')
 assert gps_check(35.7,51.4,None,None)==(None,'no_customer_gps')
 assert gps_check(0,0,35.7,51.4)[1]=='no_visit_gps' and not valid_point(91,0)
 assert gps_check(35.7,51.4,35.7005,51.4,10)[1]=='out_of_range'
def test_suggest_route_nearest_neighbor_and_coverage():
 c=[{'id':1,'lat':35.70,'lng':51.40,'last_visit':date(2026,9,1)},{'id':2,'lat':35.71,'lng':51.41,'last_visit':None},{'id':3,'lat':35.80,'lng':51.5,'last_visit':date(2026,9,2)},{'id':4,'lat':None,'lng':None,'last_visit':None},{'id':5,'lat':35.701,'lng':51.401,'last_visit':date(2026,8,1)}]
 assert [x['id'] for x in suggest_route(c,10,(35.80,51.5))]==[3,2,5,1,4]
 r=suggest_route(c,3);assert {x['id'] for x in r}=={2,4,5} and r[-1]['id']==4 and r[-1]['distance_km'] is None  # قدیمی‌ترین ویزیت‌ها انتخاب می‌شوند
 assert [x['sequence'] for x in r]==[1,2,3] and suggest_route([],5)==[]

# ───────── مرحله ۱۳: مسافت، زمان حضور، کاهش نقاط ─────────
from datetime import datetime,timedelta
from app.services.geo import detect_stays,thin_points,track_distance_m
T0=datetime(2026,10,7,9,0)
def _p(i,lat=35.7,lng=51.4,m=None): return {'lat':lat,'lng':lng,'t':T0+timedelta(minutes=i if m is None else m)}
def test_track_distance_ignores_gps_jumps():
 pts=[_p(0),_p(1,35.7009),_p(2,35.7018),{'lat':36.7,'lng':51.4,'t':T0+timedelta(minutes=2,seconds=1)},_p(3,35.7027)]
 d=track_distance_m(pts);assert 150<d<400  # پرش ~۱۱۰km در ۱ ثانیه شمرده نمی‌شود
 assert track_distance_m([])==0.0 and track_distance_m([_p(0)])==0.0
def test_detect_stays_presence_minutes_and_gap():
 A={'id':1,'name':'A','lat':35.7,'lng':51.4};B={'id':2,'name':'B','lat':35.8,'lng':51.5}
 pts=[_p(i) for i in range(0,10)]+[_p(i,35.8,51.5) for i in range(20,26)]
 s=detect_stays(pts,[A,B],150,3)
 assert [(x['place_id'],x['minutes']) for x in s]==[(1,9.0),(2,5.0)]
 # عبور کوتاه (۲ دقیقه) حضور حساب نمی‌شود
 assert detect_stays([_p(0),_p(1),_p(2)],[A],150,3)==[]
 # فاصله‌ی زمانی بیش از max_gap حضور را قطع می‌کند
 g=[_p(0),_p(5),_p(40),_p(46)];assert [x['minutes'] for x in detect_stays(g,[A],150,3,max_gap_min=15)]==[5.0,6.0]
 # بیرون از شعاع = حضور نیست؛ شعاع اختصاصی مکان رعایت می‌شود
 far=[_p(i,35.7030) for i in range(8)];assert detect_stays(far,[A],150,3)==[] and len(detect_stays(far,[{**A,'radius_m':500}],150,3))==1
 assert detect_stays(pts,[{'id':9,'lat':None,'lng':None}],150,3)==[]
def test_detect_stays_nearest_place_wins():
 A={'id':1,'name':'A','lat':35.7000,'lng':51.4};B={'id':2,'name':'B','lat':35.7008,'lng':51.4}
 s=detect_stays([_p(i,35.7007) for i in range(6)],[A,B],150,3);assert len(s)==1 and s[0]['place_id']==2
def test_thin_points_keeps_endpoints():
 pts=list(range(1000));r=thin_points(pts,10);assert len(r)==10 and r[0]==0 and r[-1]==999 and thin_points(pts[:5],10)==pts[:5]
