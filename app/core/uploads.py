from __future__ import annotations
import os
import uuid
from fastapi import HTTPException
from app.core.config import ROOT
from app.models import Document

def store_image(s,cid,entity,eid,data,max_bytes):
 """ذخیره‌ی تصویر (نوع واقعی با magic bytes) به‌صورت Document؛ فراخوان باید commit کند."""
 from app.services.files import sniff_type
 if len(data)>max_bytes: raise HTTPException(413,'حجم فایل بیش از حد مجاز است')
 ty=sniff_type(data) if data else None
 if not ty or ty[0] not in ('png','jpg','webp'): raise HTTPException(400,'فقط تصویر PNG، JPG یا WebP مجاز است')
 folder=os.path.join(ROOT,'uploads',str(cid));os.makedirs(folder,exist_ok=True);path=os.path.join(folder,f'{uuid.uuid4().hex}.{ty[0]}')
 with open(path,'wb') as f: f.write(data)
 import hashlib
 doc=Document(company_id=cid,entity=entity,entity_id=eid,filename=f'{entity}-{eid}.{ty[0]}',path=path,size=len(data),mime=ty[1],sha256=hashlib.sha256(data).hexdigest());s.add(doc);s.flush();return doc,len(data)
