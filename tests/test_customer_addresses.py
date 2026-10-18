import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_addr.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'}); assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def cust(h,code):
 r=client.post('/api/customers',headers=h,json={'code':code,'name':'c'+code}); assert r.status_code==200,r.text; return r.json()['id']

def test_first_address_is_default_and_syncs_legacy_fields():
 h=H(); c=cust(h,'AD1')
 a=client.post(f'/api/customers/{c}/addresses',headers=h,json={'title':'انبار','address':'تهران','region':'R1','lat':35.7,'lng':51.4}); assert a.status_code==200,a.text
 assert a.json()['is_default'] is True
 d=client.get(f'/api/customers/{c}',headers=h).json(); assert d['address']=='تهران' and d['lat']==35.7 and len(d['addresses'])==1
 b=client.post(f'/api/customers/{c}/addresses',headers=h,json={'title':'شعبه','address':'کرج','lat':35.8,'lng':50.9,'is_default':True}).json()
 lst=client.get(f'/api/customers/{c}/addresses',headers=h).json(); assert [x['is_default'] for x in lst]==[True,False] and lst[0]['id']==b['id']
 assert client.get(f'/api/customers/{c}',headers=h).json()['address']=='کرج'

def test_default_address_rules_and_soft_delete():
 h=H(); c=cust(h,'AD2')
 a1=client.post(f'/api/customers/{c}/addresses',headers=h,json={'title':'الف'}).json(); a2=client.post(f'/api/customers/{c}/addresses',headers=h,json={'title':'ب'}).json()
 assert client.delete(f'/api/customers/{c}/addresses/{a1["id"]}',headers=h).status_code==409
 assert client.patch(f'/api/customers/{c}/addresses/{a1["id"]}',headers=h,json={'is_default':False}).status_code==409
 assert client.patch(f'/api/customers/{c}/addresses/{a2["id"]}',headers=h,json={'is_default':True}).status_code==200
 assert client.delete(f'/api/customers/{c}/addresses/{a1["id"]}',headers=h).status_code==200
 assert [x['id'] for x in client.get(f'/api/customers/{c}/addresses',headers=h).json()]==[a2['id']]
 assert client.delete(f'/api/customers/{c}/addresses/{a1["id"]}',headers=h).status_code==404
 assert client.post(f'/api/customers/{c}/addresses',headers=h,json={'title':'x','lat':999}).status_code==422

def test_addresses_are_scoped_to_their_customer():
 h=H(); c1=cust(h,'AD3'); c2=cust(h,'AD4')
 a=client.post(f'/api/customers/{c1}/addresses',headers=h,json={'title':'t'}).json()
 assert client.patch(f'/api/customers/{c2}/addresses/{a["id"]}',headers=h,json={'title':'hack'}).status_code==404
 assert client.get('/api/customers/999999/addresses',headers=h).status_code==404

def test_primary_contact_switching_and_delete_promotes_next():
 h=H(); c=cust(h,'CT1')
 k1=client.post(f'/api/customers/{c}/contacts',headers=h,json={'name':'علی','phone':'0912'}).json(); k2=client.post(f'/api/customers/{c}/contacts',headers=h,json={'name':'رضا'}).json()
 assert k1['is_primary'] is True and k2['is_primary'] is False
 assert client.patch(f'/api/customers/{c}/contacts/{k2["id"]}',headers=h,json={'is_primary':True}).status_code==200
 assert [x['is_primary'] for x in client.get(f'/api/customers/{c}/contacts',headers=h).json()]==[True,False]
 assert client.delete(f'/api/customers/{c}/contacts/{k2["id"]}',headers=h).status_code==200
 rest=client.get(f'/api/customers/{c}/contacts',headers=h).json(); assert len(rest)==1 and rest[0]['id']==k1['id'] and rest[0]['is_primary'] is True
