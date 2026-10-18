import os,re,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_perm.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from app.main import app,required_perm,PUBLIC_PATHS,OPEN_PATHS,ALL_PERMS
client=TestClient(app)
PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def role_id(H,name):
 client.post('/api/roles/templates',headers=H)
 return next(r['id'] for r in client.get('/api/roles',headers=H).json() if r['name']==name)
def mkuser(H,role):
 u='u'+uuid.uuid4().hex[:8];rid=role if isinstance(role,int) else role_id(H,role)
 r=client.post('/api/users',headers=H,json={'branch_id':1,'username':u,'password':PW,'name':u,'role_id':rid,'company_ids':[]})
 if r.status_code==404: r=client.post('/api/users',headers=H,json={'username':u,'password':PW,'name':u,'role_id':rid,'company_ids':[]})  # شرکت دیگر: شعبهٔ ۱ مال آن نیست
 assert r.status_code==200,r.text
 return login(u,PW)

def test_every_api_route_has_explicit_permission_or_is_whitelisted():
 open_ok=set()
 for r in app.routes:
  if not isinstance(r,APIRoute) or not r.path.startswith('/api/'): continue
  path=re.sub(r'\{[^}]+\}','1',r.path)
  for m in r.methods-{'HEAD','OPTIONS'}:
   p=required_perm(m,path)
   if p is None:
    assert path.startswith(PUBLIC_PATHS+OPEN_PATHS) or (m=='GET' and path=='/api/settings/brand'),f'{m} {r.path} بدون permission'
    open_ok.add((m,r.path))
   else:
    assert p in ALL_PERMS or p=='admin.write',f'{m} {r.path} -> {p} ناشناخته'
 # مسیرهای باز فقط همین‌ها هستند
 assert all(path.startswith(PUBLIC_PATHS+OPEN_PATHS) or path=='/api/settings/brand' for _,path in open_ok)

def test_unknown_api_path_is_denied_by_default():
 assert required_perm('GET','/api/something-new')=='admin.write'
 assert required_perm('POST','/api/auth/login') is None
 assert required_perm('GET','/api/reports/profit-loss')=='finance.read'
 assert required_perm('GET','/api/reports/trial-balance.xlsx')=='finance.read'
 assert required_perm('GET','/api/customers/5/ledger')=='finance.read'
 assert required_perm('GET','/api/reports/sales')=='reports.read'
 assert required_perm('GET','/api/dashboard/trend')=='sales.read'

def test_unauthenticated_requests_rejected():
 for m,u in [('get','/api/customers'),('get','/api/dashboard'),('get','/api/search?q=a'),('post','/api/sync'),('get','/api/me'),('get','/api/reports/trial-balance')]:
  assert client.request(m.upper(),u,json={} if m!='get' else None).status_code==401,u

# (role, method, url, allowed)
MATRIX=[
 ('فروشنده','GET','/api/customers',True),('فروشنده','GET','/api/products',True),('فروشنده','POST','/api/orders',True),
 ('فروشنده','GET','/api/journal',False),('فروشنده','GET','/api/reports/trial-balance',False),('فروشنده','GET','/api/audit',False),
 ('فروشنده','POST','/api/stock/adjust',False),('فروشنده','GET','/api/employees',False),('فروشنده','GET','/api/customers/1/ledger',False),
 ('فروشنده','POST','/api/orders/1/approve',False),('فروشنده','GET','/api/reports/sales',False),('فروشنده','POST','/api/users',False),
 ('حسابدار','GET','/api/reports/trial-balance',True),('حسابدار','GET','/api/reports/profit-loss',True),('حسابدار','GET','/api/journal',True),
 ('حسابدار','GET','/api/customers/1/ledger',True),('حسابدار','POST','/api/stock/adjust',False),('حسابدار','POST','/api/users',False),
 ('حسابدار','POST','/api/orders',False),('حسابدار','GET','/api/audit',False),
 ('انباردار','POST','/api/stock/adjust',True),('انباردار','GET','/api/journal',False),('انباردار','POST','/api/payments',False),('انباردار','GET','/api/reports/aging',False),
 ('مأمور پخش','GET','/api/deliveries',True),('مأمور پخش','PATCH','/api/deliveries/1',True),('مأمور پخش','GET','/api/customers',False),
 ('مأمور پخش','GET','/api/products',False),('مأمور پخش','GET','/api/reports/profit-loss',False),('مأمور پخش','POST','/api/orders',False),
 ('مدیر فروش','GET','/api/reports/sales',True),('مدیر فروش','POST','/api/orders/1/approve',True),
 ('مدیر فروش','GET','/api/reports/profit-loss',False),('مدیر فروش','GET','/api/reports/balance-sheet',False),('مدیر فروش','GET','/api/journal',False),
 ('بازاریاب','POST','/api/visits',True),('بازاریاب','POST','/api/visits/1/photo',True),('مأمور پخش','POST','/api/deliveries/bulk-assign',False),('مدیر فروش','POST','/api/deliveries/bulk-assign',True),('بازاریاب','POST','/api/leads',True),('بازاریاب','POST','/api/tasks',True),('فروشنده','POST','/api/proposals',True),('مأمور پخش','POST','/api/leads',False),('حسابدار','POST','/api/tasks',False),('انباردار','POST','/api/proposals',False),('بازاریاب','POST','/api/payments',True),('بازاریاب','POST','/api/journal',False),('بازاریاب','POST','/api/stock/adjust',False),
]
def test_permission_matrix_per_role():
 A=login();cache={}
 for role,m,url,allowed in MATRIX:
  H=cache.get(role) or cache.setdefault(role,mkuser(A,role))
  code=client.request(m,url,headers=H,json={} if m!='GET' else None).status_code
  assert (code!=403)==allowed,f'{role} {m} {url} -> {code}'

def test_dashboard_masks_fields_by_permission():
 A=login();seller=mkuser(A,'فروشنده');acc=mkuser(A,'حسابدار');drv=mkuser(A,'مأمور پخش')
 d=client.get('/api/dashboard',headers=seller);assert d.status_code==200
 assert d.json()['receivables'] is None and d.json()['payments_today'] is None and d.json()['sales_today'] is not None
 d=client.get('/api/dashboard',headers=acc).json();assert d['receivables'] is not None and d['stock_value'] is None
 d=client.get('/api/dashboard',headers=drv).json();assert d['receivables'] is None and d['stock_value'] is None and d['customers'] is None and d['active_deliveries'] is not None
 assert client.get('/api/dashboard',headers=A).json()['receivables'] is not None
 lo=client.post('/api/roles',headers=A,json={'name':'فقط-مشتری-'+uuid.uuid4().hex[:5],'permissions':['crm.read']}).json()['id'];L=mkuser(A,lo)
 assert client.get('/api/dashboard/trend',headers=L).status_code==403 and client.get('/api/dashboard/by-category',headers=L).status_code==403
 assert client.get('/api/dashboard/trend',headers=A).status_code==200

def test_search_respects_permissions_and_scope():
 A=login();sfx=uuid.uuid4().hex[:6]
 assert client.post('/api/customers',headers=A,json={'code':'S'+sfx,'name':'zzsearch'+sfx}).status_code==200
 assert client.get('/api/search?q=zzsearch'+sfx,headers=A).json()['customers']
 drv=mkuser(A,'مأمور پخش');r=client.get('/api/search?q=zzsearch'+sfx,headers=drv).json()
 assert r=={'customers':[],'products':[],'orders':[]}
 seller=mkuser(A,'فروشنده');assert client.get('/api/search?q=zzsearch'+sfx,headers=seller).json()['customers']
 assert client.get('/api/search?q=%25%25%25',headers=A).json()['customers']==[]
 assert client.get('/api/search?q='+'x'*101,headers=A).status_code==422

def test_tenant_isolation_between_companies():
 A=login();sfx=uuid.uuid4().hex[:6]
 c=client.post('/api/customers',headers=A,json={'code':'T'+sfx,'name':'مشتری-الف-'+sfx,'credit_limit':1000}).json()
 p=client.post('/api/products',headers=A,json={'sku':'T'+sfx,'name':'کالا','base_price':100}).json()
 w=client.get('/api/warehouses',headers=A).json()[0]
 client.post('/api/stock/adjust',headers=A,json={'warehouse_id':w['id'],'product_id':p['id'],'quantity':10,'kind':'in'})
 o=client.post('/api/orders',headers=A,json={'customer_id':c['id'],'warehouse_id':w['id'],'items':[{'product_id':p['id'],'quantity':2}]}).json()
 assert client.post(f"/api/orders/{o['id']}/approve",headers=A).status_code==200
 inv=next(i for i in client.get('/api/invoices',headers=A).json() if i['order_id']==o['id'])
 b=client.post('/api/organizations/company',headers=A,json={'name':'شرکت ب '+sfx,'code':'B'+sfx});assert b.status_code==200,b.text
 tok=client.post('/api/auth/switch-company',params={'company_id':b.json()['id']},headers=A).json()['token'];AB={'Authorization':'Bearer '+tok}
 rid=client.post('/api/roles',headers=AB,json={'name':'ب-نقش','permissions':['crm.write','sales.write','finance.read','catalog.read','inventory.read']}).json()['id']
 u='b'+sfx;assert client.post('/api/users',headers=AB,json={'username':u,'password':PW,'name':u,'role_id':rid,'company_ids':[]}).status_code==200
 B=login(u,PW)
 assert client.get('/api/me',headers=B).json()['company']['id']==b.json()['id']
 assert all(x['id']!=c['id'] for x in client.get('/api/customers',headers=B).json())
 assert all(x['id']!=p['id'] for x in client.get('/api/products',headers=B).json())
 assert all(x['id']!=o['id'] for x in client.get('/api/orders',headers=B).json())
 assert client.get(f"/api/customers/{c['id']}/ledger",headers=B).status_code==404
 assert client.get(f"/api/invoices/{inv['id']}",headers=B).status_code==404
 assert client.get('/api/search?q='+sfx,headers=B).json()=={'customers':[],'products':[],'orders':[]}
 assert float(client.get('/api/reports/trial-balance',headers=B).json()['total_debit'])==0
 # B کاربر نمی‌تواند به شرکت الف سوییچ کند
 assert client.post('/api/auth/switch-company',params={'company_id':1},headers=B).status_code==403
 # B فاکتور/سفارش الف را با شناسه تأیید/لغو نمی‌کند
 BA=client.post('/api/roles',headers=AB,json={'name':'ب-تأییدکننده','permissions':['sales.approve','sales.write']}).json()['id']
 B2=mkuser(AB,BA)
 assert client.post(f"/api/orders/{o['id']}/cancel",headers=B2).status_code in (403,404)
