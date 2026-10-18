"""ذخیره‌ی امن فایل: تشخیص نوع واقعی (magic bytes + ساختار zip برای docx/xlsx)، محدودیت حجم، اسکن آنتی‌ویروس اختیاری (ClamAV)،
نام تصادفی روی دیسک و هش SHA-256.

ClamAV: اگر `CLAMAV_HOST` تنظیم شود هر فایل با پروتکل INSTREAM به clamd (پورت `CLAMAV_PORT`، پیش‌فرض ۳۳۱۰) می‌رود؛
فایل آلوده رد می‌شود. اگر clamd در دسترس نباشد: با `CLAMAV_REQUIRED=1` آپلود رد می‌شود (۵۰۳)، وگرنه هشدار لاگ و ادامه.
"""
from __future__ import annotations
import hashlib
import io
import logging
import os
import socket
import struct
import uuid
import zipfile
from fastapi import HTTPException
from app.core.config import ROOT, UPLOAD_DIR

log=logging.getLogger('abtin')
MAX_UNZIPPED=100*1024*1024
DOCX='application/vnd.openxmlformats-officedocument.wordprocessingml.document';XLSX='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
def _ooxml(b):
 """docx/xlsx واقعی: zip سالم با فایل‌های شاخص و بدون بمب فشرده‌سازی"""
 try:
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   if sum(i.file_size for i in z.infolist())>MAX_UNZIPPED or z.testzip() is not None: return None
   n=set(z.namelist())
   if '[Content_Types].xml' in n and 'word/document.xml' in n: return 'docx',DOCX
   if '[Content_Types].xml' in n and 'xl/workbook.xml' in n: return 'xlsx',XLSX
 except (zipfile.BadZipFile,RuntimeError,OSError): return None
 return None
def sniff_type(b):
 if b[:5]==b'%PDF-': return 'pdf','application/pdf'
 if b[:8]==b'\x89PNG\r\n\x1a\n': return 'png','image/png'
 if b[:3]==b'\xff\xd8\xff': return 'jpg','image/jpeg'
 if b[:4]==b'RIFF' and b[8:12]==b'WEBP': return 'webp','image/webp'
 if b[:4]==b'PK\x03\x04': return _ooxml(b)
 return None
def av_scan(data):
 """None = تمیز یا اسکن غیرفعال؛ رشته = نام تهدید. خطای اتصال طبق CLAMAV_REQUIRED رفتار می‌کند."""
 host=os.getenv('CLAMAV_HOST','')
 if not host: return None
 try:
  with socket.create_connection((host,int(os.getenv('CLAMAV_PORT','3310'))),timeout=15) as c:
   c.sendall(b'zINSTREAM\0')
   for i in range(0,len(data),65536):
    ch=data[i:i+65536];c.sendall(struct.pack('!I',len(ch))+ch)
   c.sendall(struct.pack('!I',0));resp=b''
   while not resp.endswith(b'\0') and len(resp)<1024:
    d=c.recv(1024)
    if not d: break
    resp+=d
 except OSError as e:
  if os.getenv('CLAMAV_REQUIRED','')=='1': raise HTTPException(503,'سرویس آنتی‌ویروس در دسترس نیست؛ آپلود موقتاً ممکن نیست')
  log.warning('ClamAV unreachable, upload not scanned: %s',e);return None
 r=resp.rstrip(b'\0').decode('utf-8','replace')
 if r.endswith('FOUND'): return r.split(':',1)[-1].replace('FOUND','').strip() or 'infected'
 if r.endswith('ERROR') and os.getenv('CLAMAV_REQUIRED','')=='1': raise HTTPException(503,'اسکن آنتی‌ویروس ناموفق بود')
 return None
def store_bytes(cid,data,max_bytes,allowed=None):
 """اعتبارسنجی + اسکن + نوشتن روی دیسک. خروجی: dict(path,ext,mime,size,sha256). خطا → HTTPException"""
 if not data: raise HTTPException(400,'فایل خالی است')
 if len(data)>max_bytes: raise HTTPException(413,'حجم فایل بیش از حد مجاز است')
 t=sniff_type(data)
 if not t or (allowed and t[0] not in allowed): raise HTTPException(400,'نوع فایل مجاز نیست (PDF، PNG، JPG، WebP، DOCX، XLSX)')
 threat=av_scan(data)
 if threat: raise HTTPException(422,f'فایل آلوده شناسایی شد و ذخیره نشد ({threat})')
 folder=os.path.join(UPLOAD_DIR,str(cid));os.makedirs(folder,exist_ok=True);path=os.path.join(folder,f'{uuid.uuid4().hex}.{t[0]}')
 with open(path,'xb') as f: f.write(data)
 return {'path':path,'ext':t[0],'mime':t[1],'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
