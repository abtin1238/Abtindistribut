import io,os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_import.sqlite3')
os.environ['ADMIN_PASSWORD']='test-password'
import openpyxl
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def H():
 r=client.post('/api/auth/login',json={'username':'admin','password':'test-password'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def xlsx(rows):
 wb=openpyxl.Workbook();ws=wb.active
 for r in rows: ws.append(r)
 b=io.BytesIO();wb.save(b);return b.getvalue()
def post(h,path,data,**form): return client.post('/api/import/'+path,headers=h,files={'file':('x.xlsx',data)},data=form)
def test_products_stock_import_idempotent():
 h=H();d=xlsx([['گزارش موجودی'],[],['ردیف','کد کالا','نام کالا','واحد','موجودی','قیمت فروش'],[1,'IMP1','نوشابه','عدد','1,250','۴۵٬۰۰۰'],[2,'IMP2','آب','کارتن',30,12000],[3,'IMP3','بد','عدد','x',1]])
 p=post(h,'preview',d);assert p.status_code==200,p.text;j=p.json()
 assert j['entity']=='products' and j['summary']['new']==2 and j['summary']['error']==1
 assert not any(x['sku']=='IMP1' for x in client.get('/api/products',headers=h).json())  # پیش‌نمایش چیزی ننوشته
 c=post(h,'commit',d);assert c.status_code==200 and c.json()['applied'] and c.json()['summary']['new']==2,c.text
 st=[x for x in client.get('/api/stock',headers=h).json() if x['sku']=='IMP1'];assert st and float(st[0]['quantity'])==1250
 c2=post(h,'commit',d).json();assert c2['summary']['new']==0 and c2['summary']['update']==0 and c2['summary']['unchanged']==2
 assert post(h,'commit',d,strict='true').status_code==409
def test_customer_balance_adjusts_ledger_and_is_idempotent():
 h=H();d=xlsx([['کد مشتری','نام مشتری','تلفن','بدهکار','بستانکار'],['IC1','مشتری وارداتی','9121234567','1,000',''],['IC2','مشتری بستانکار','','','500']])
 assert post(h,'commit',d).json()['summary']['new']==2
 cs={x['code']:x for x in client.get('/api/customers',headers=h).json()};assert float(cs['IC1']['balance'])==1000 and float(cs['IC2']['balance'])==-500 and cs['IC1']['phone']=='09121234567'
 s=post(h,'commit',d).json()['summary'];assert s['new']==0 and s['update']==0
 d2=xlsx([['کد مشتری','نام مشتری','بدهکار','بستانکار'],['IC1','مشتری وارداتی','400','']])
 assert post(h,'commit',d2).json()['summary']['update']==1
 assert float({x['code']:x for x in client.get('/api/customers',headers=h).json()}['IC1']['balance'])==400
def test_permissions_and_bad_files():
 assert client.post('/api/import/preview',files={'file':('x.xlsx',b'1')}).status_code==401
 h=H();assert post(h,'preview',b'PK\x03\x04junk').status_code==400
 assert post(h,'preview',xlsx([['کد کالا','نام کالا'],['A','b']]),entity='nope').status_code==400
