import os,uuid
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_approute.sqlite3');os.environ.setdefault('ADMIN_PASSWORD','test-password')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
PW='Pw-test-1'
def login(u='admin',p=None):
 r=client.post('/api/auth/login',json={'username':u,'password':p or os.environ['ADMIN_PASSWORD']});assert r.status_code==200,r.text
 return r.json()
def H(d): return {'Authorization':'Bearer '+d['token']}
def role_id(h,name):
 client.post('/api/roles/templates',headers=h)
 return next(r['id'] for r in client.get('/api/roles',headers=h).json() if r['name']==name)
def mk(h,role,branch=None,expect=200):
 u='u'+uuid.uuid4().hex[:8]
 r=client.post('/api/users',headers=h,json={'username':u,'password':PW,'name':u,'role_id':role_id(h,role),'company_ids':[],'branch_id':branch})
 assert r.status_code==expect,r.text
 return u

def test_login_routes_each_role_to_its_own_app():
 h=H(login())
 assert login()['app']=='panel'
 for role,app_,home in [('بازاریاب','visitor','/mobile/visitor/'),('مأمور پخش','driver','/mobile/driver/'),('فروشنده','panel','/web/'),('مدیر فروش','panel','/web/'),('حسابدار','panel','/web/'),('انباردار','panel','/web/')]:
  d=login(mk(h,role,branch=1 if role=='مدیر فروش' else None),PW)
  assert (d['app'],d['home'])==(app_,home),role
  assert client.get('/api/me',headers=H(d)).json()['user']['app']==app_

def test_manager_template_is_not_super_admin():
 h=H(login());rs=client.get('/api/roles',headers=h).json();client.post('/api/roles/templates',headers=h)
 rs=client.get('/api/roles',headers=h).json();m=next(r for r in rs if r['name']=='مدیر شرکت')
 assert '*' not in m['permissions'] and not {'admin.write','settings.write','ceo.read'}&set(m['permissions'])

def test_manager_needs_branch_and_sees_only_it():
 h=H(login());cid=client.get('/api/me',headers=h).json()['company']['id']
 a=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'A'}).json()['id']
 b=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'B'}).json()['id']
 wa=client.post('/api/warehouses',headers=h,json={'company_id':cid,'branch_id':a,'name':'WA'}).json()['id']
 wb=client.post('/api/warehouses',headers=h,json={'company_id':cid,'branch_id':b,'name':'WB'}).json()['id']
 mk(h,'مدیر شرکت',None,expect=400)
 mh=H(login(mk(h,'مدیر شرکت',a),PW))
 ids={w['id'] for w in client.get('/api/warehouses',headers=mh).json()}
 assert wa in ids and wb not in ids
 assert {w['id'] for w in client.get('/api/warehouses',headers=h).json()}>={wa,wb}
 assert client.get('/api/users',headers=mh).status_code==403

def test_field_roles_blocked_from_panel_client_but_not_their_own_app():
 h=H(login())
 for role in ('بازاریاب','مأمور پخش'):
  d=login(mk(h,role),PW);ph={**H(d),'X-Client':'panel'}
  assert client.get('/api/customers',headers=ph).status_code==403 or client.get('/api/deliveries',headers=ph).status_code==403
  assert client.get('/api/me',headers=ph).status_code==200
 d=login(mk(h,'فروشنده'),PW)
 assert client.get('/api/customers',headers={**H(d),'X-Client':'panel'}).status_code==200

def test_audit_has_user_name_and_manager_purchases_scoped():
 h=H(login());a=client.get('/api/audit',headers=h).json()
 assert a and 'user_name' in a[0]
 cid=client.get('/api/me',headers=h).json()['company']['id']
 ba=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'PA'}).json()['id']
 bb=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'PB'}).json()['id']
 wa=client.post('/api/warehouses',headers=h,json={'company_id':cid,'branch_id':ba,'name':'PWA'}).json()['id']
 wb=client.post('/api/warehouses',headers=h,json={'company_id':cid,'branch_id':bb,'name':'PWB'}).json()['id']
 sid=client.post('/api/suppliers',headers=h,json={'name':'S'}).json()['id']
 pid=client.post('/api/products',headers=h,json={'name':'P','sku':'SKU'+uuid.uuid4().hex[:6],'base_price':10}).json()['id']
 mk_p=lambda w:client.post('/api/purchases',headers=h,json={'supplier_id':sid,'warehouse_id':w,'items':[{'product_id':pid,'quantity':1,'unit_cost':5}]}).json()['id']
 pa,pb=mk_p(wa),mk_p(wb)
 mh=H(login(mk(h,'مدیر شرکت',ba),PW))
 got={x['id'] for x in client.get('/api/purchases',headers=mh).json()}
 assert pa in got and pb not in got
 assert client.get(f'/api/purchases/{pb}',headers=mh).status_code==404

def test_customers_bound_to_branch_for_manager():
 h=H(login());cid=client.get('/api/me',headers=h).json()['company']['id']
 a=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'CA'}).json()['id']
 b=client.post('/api/organizations/branch',headers=h,json={'company_id':cid,'name':'CB'}).json()['id']
 sfx=uuid.uuid4().hex[:6]
 ca=client.post('/api/customers',headers=h,json={'code':'A'+sfx,'name':'ca','branch_id':a}).json()['id']
 cb=client.post('/api/customers',headers=h,json={'code':'B'+sfx,'name':'cb','branch_id':b}).json()['id']
 mh=H(login(mk(h,'مدیر شرکت',a),PW))
 ids={x['id'] for x in client.get('/api/customers',headers=mh).json()}
 assert ca in ids and cb not in ids
 assert client.get(f'/api/customers/{cb}',headers=mh).status_code==404 and client.get(f'/api/customers/{ca}',headers=mh).status_code==200
 mine=client.post('/api/customers',headers=mh,json={'code':'M'+sfx,'name':'cm','branch_id':b}).json()
 assert mine['branch_id']==a   # مدیر نمی‌تواند برای شعبهٔ دیگر مشتری بسازد
 assert client.post('/api/customers',headers=h,json={'code':'X'+sfx,'name':'x','branch_id':999999}).status_code==404
