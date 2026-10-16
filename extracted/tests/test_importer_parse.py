import io
from decimal import Decimal
import openpyxl
from app.services.importer import ImportError_,cell_text,coerce_rows,detect,load_tables,map_headers,parse_num,norm_phone
def xlsx(rows,sheet='Sheet1'):
 wb=openpyxl.Workbook();ws=wb.active;ws.title=sheet
 for r in rows: ws.append(r)
 b=io.BytesIO();wb.save(b);return b.getvalue()
def run(data,entity=None):
 t=next(iter(load_tables(data).values()));hr,e,_=detect(t);e=entity or e
 m={i:f for i,(f,_) in map_headers(e,[str(c or '') for c in t[hr]]).items()};return e,hr,m,coerce_rows(e,t,hr,m)
def test_holoo_products_with_title_repeated_header_totals():
 d=xlsx([['شرکت نمونه — گزارش موجودی کالا'],['تاریخ: ۱۴۰۵/۰۶/۱۰'],[],['ردیف','کد کالا','نام کالا','واحد','موجودی','قیمت فروش'],[1,'۰۰۱۲','نوشابه ۱.۵ لیتری ك','عدد','1,250','۴۵٬۰۰۰'],[2,'A-7','آب معدني','کارتن',30.0,'(5,000)'],['ردیف','کد کالا','نام کالا','واحد','موجودی','قیمت فروش'],[3,'0013','چیپس','عدد',10,12000],['','','جمع','',1290,'']])
 e,hr,m,rows=run(d);assert e=='products' and hr==3 and set(m.values())>={'sku','name','unit','quantity','base_price'}
 ok=[r for r in rows if not r['skip']];assert len(ok)==3
 assert ok[0]['values']['sku']=='0012' and ok[0]['values']['name']=='نوشابه ۱.۵ لیتری ک'.replace('۱.۵','1.5') and ok[0]['values']['quantity']==Decimal(1250) and ok[0]['values']['base_price']==Decimal(45000)
 assert ok[1]['errors'] and 'منفی' in ok[1]['errors'][0] and ok[1]['values']['name']=='آب معدنی'
 assert not ok[2]['errors'] and any(r['skip'] for r in rows)
def test_customers_debit_credit_and_type():
 d=xlsx([['کد مشتری','نام مشتری','تلفن همراه','بدهکار','بستانکار'],[1,'علی','9121234567','1,000',''],[2,'رضا','+989121111111','','500'],[3,'علی','','',''] ])
 e,hr,m,rows=run(d);assert e=='customers';v=[r['values'] for r in rows]
 assert v[0]['_balance']==1000 and v[1]['_balance']==-500 and v[0]['phone']=='09121234567' and v[1]['phone']=='09121111111'
 d=xlsx([['نام طرف حساب','مانده','تشخیص'],['الف','2,000','بس'],['ب','300','بد']])
 e,hr,m,rows=run(d,'suppliers');assert [r['values']['_balance'] for r in rows]==[2000,-300]
 e,hr,m,rows=run(d,'customers');assert [r['values']['_balance'] for r in rows]==[-2000,300]
def test_duplicates_and_bad_numbers():
 d=xlsx([['کد کالا','نام کالا','موجودی'],['1','x','abc'],['1','y',5]])
 e,hr,m,rows=run(d,'stock');assert 'عدد نامعتبر' in rows[0]['errors'][0] and 'تکراری' in rows[1]['errors'][0]
def test_csv_cp1256_html_and_json():
 csv='کد کالا;نام کالا;قيمت\n1;چاي;10,000\n'.encode('cp1256');t=next(iter(load_tables(csv).values()));assert cell_text(t[1][1])=='چای'
 h=('<html><meta charset=utf-8><table><tr><th>کد مشتری</th><th>نام مشتری</th></tr><tr><td>5</td><td>سعید</td></tr></table></html>').encode();t=next(iter(load_tables(h).values()));assert t[1]==['5','سعید']
 j=b'{"data":[{"sku":"1","name":"a","price":5}]}';t=next(iter(load_tables(j).values()));assert t[0]==['sku','name','price']
 assert map_headers('products',t[0]).get(0)[0]=='sku'
def test_rejects_garbage():
 for b in (b'',b'PK\x03\x04junk'):
  try: load_tables(b);assert False
  except ImportError_: pass
def test_numbers_and_phone():
 assert parse_num('۱٬۲۳۴')==1234 and parse_num('12-')==-12 and parse_num('')is None and parse_num('1500 ریال')==1500
 for bad in ('12a','1.2.3'):
  try: parse_num(bad);assert False
  except ValueError: pass
 assert norm_phone('021-12345678 / 0912')=='02112345678'
def test_buy_price_not_mapped_as_sale_price():
 m=map_headers('products',['کد کالا','نام کالا','قیمت خرید','قیمت فروش']);assert m[3][0]=='base_price' and 2 not in m
