"""تست‌های خالص (بدون FastAPI/DB): تاریخ شمسی و خروجی Excel/PDF"""
import io,pytest
from datetime import date,timedelta
from decimal import Decimal
from app.services.jalali import from_jalali,parse_jalali,to_jalali
def test_jalali_roundtrip():
 d=date(1995,1,1)
 while d<date(2045,1,1): assert from_jalali(*to_jalali(d))==d;d+=timedelta(7)
def test_parse_jalali_persian_digits_and_invalid():
 assert parse_jalali('۱۴۰۵/۰۷/۱۹')==date(2026,10,11)
 for bad in ('1405/13/01','1405/07/32','1405/12/30','x','1405/7'):
  with pytest.raises(ValueError): parse_jalali(bad)
TBL={'title':'گزارش','columns':[{'key':'n','label':'نام','kind':'text'},{'key':'d','label':'تاریخ','kind':'date'},{'key':'m','label':'مبلغ','kind':'money'}],'rows':[{'n':'=SUM(A1)','d':'2026-10-10','m':Decimal('1500')},{'n':'ب','d':None,'m':None}],'summary':[['جمع',Decimal(1500),'money']],'filters':{'start':'2026-10-01'}}
def test_xlsx_neutralizes_formulas_and_converts_dates():
 pytest.importorskip('openpyxl');from openpyxl import load_workbook;from app.services.exporters import to_xlsx
 rows=list(load_workbook(io.BytesIO(to_xlsx(TBL))).active.iter_rows(values_only=True))
 hdr=next(i for i,r in enumerate(rows) if r[0]=='نام');assert rows[hdr+1]==("'=SUM(A1)",'1405/07/18',1500.0) and rows[hdr+2][1] is None
def test_pdf_builds(monkeypatch):
 pytest.importorskip('reportlab');import app.services.exporters as ex
 monkeypatch.setattr(ex,'_shaper',lambda:(lambda s:s[::-1]))   # شکل‌دهنده‌ی واقعی در تولید: arabic-reshaper + python-bidi
 try: ex._font_path()
 except RuntimeError: pytest.skip('no font')
 assert ex.to_pdf(TBL,'شرکت').startswith(b'%PDF')
def test_pdf_requires_shaping_libs(monkeypatch):
 pytest.importorskip('reportlab');import app.services.exporters as ex
 monkeypatch.setitem(__import__('sys').modules,'arabic_reshaper',None)
 with pytest.raises(RuntimeError): ex.to_pdf(TBL)
