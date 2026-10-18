from __future__ import annotations
import os
from typing import Optional
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.common import audit, obj
from app.core.config import utcnow
from app.models import Document, FileVersion, Check, Contract, Customer, Delivery, Employee, Invoice, Order, Payment, Product, Purchase, Supplier, Visit
from app.modules.platform import MAX_UPLOAD
from app.services.files import store_bytes
from .schemas import DocPatch
import re
from app.core.security import has_all, has_perm, own_orders

# موجودیت پیوست‌پذیر: (مدل، مجوز خواندن رکورد). contract مدل ندارد و فقط با مجوز فایل کنترل می‌شود.
ENT={'customer':(Customer,'crm.read'),'product':(Product,'catalog.read'),'order':(Order,'sales.read'),'invoice':(Invoice,'sales.read'),'purchase':(Purchase,'purchase.read'),'supplier':(Supplier,'purchase.read'),'delivery':(Delivery,'delivery.read'),'visit':(Visit,'visit.read'),'employee':(Employee,'hr.read'),'check':(Check,'finance.read'),'payment':(Payment,'finance.collect'),'contract':(Contract,'files.read')}

def can_access(s,ctx,entity,eid):
 """آیا کاربر به رکوردِ مادرِ پیوست دسترسی دارد؟ (مجوز ماژول + شرکت + Data Scope)"""
 u,cid,r=ctx;m=ENT.get(entity)
 if not m: return has_all(r)   # نوع ناشناخته/قدیمی فقط برای مدیر
 model,perm=m
 if not has_perm(r,perm): return False
 if model is None: return True
 x=s.get(model,eid)
 if not x or x.company_id!=cid: return False
 if has_all(r): return True
 if entity=='order': return bool(s.scalar(select(Order.id).where(Order.id==eid,own_orders(u))))
 if entity=='invoice': return bool(s.scalar(select(Invoice.id).join(Order,Order.id==Invoice.order_id).where(Invoice.id==eid,own_orders(u))))
 if entity=='delivery': return has_perm(r,'delivery.read.all') or x.driver_id==u.id
 if entity=='visit': return x.user_id==u.id
 if entity=='payment': return bool(x.invoice_id) and bool(s.scalar(select(Invoice.id).join(Order,Order.id==Invoice.order_id).where(Invoice.id==x.invoice_id,own_orders(u))))
 return True

def visible(s,ctx,d,cache=None):
 """ACL کامل یک پیوست: حذف‌نشده، شرکت، محدودیت (restricted: فقط سازنده/مدیر) و دسترسی به رکورد مادر"""
 u,cid,r=ctx
 if d.company_id!=cid or d.deleted_at is not None: return False
 if d.restricted and not (has_all(r) or d.owner_id==u.id): return False
 k=(d.entity,d.entity_id)
 if cache is not None and k in cache: return cache[k]
 ok=can_access(s,ctx,d.entity,d.entity_id)
 if cache is not None: cache[k]=ok
 return ok

def ensure_v1(s,d):
 """پیوست‌های قدیمی (قبل از نسخه‌بندی) در اولین دسترسی نسخه‌ی ۱ می‌گیرند"""
 if s.scalar(select(FileVersion.id).where(FileVersion.document_id==d.id).limit(1)): return
 sz=d.size or (os.path.getsize(d.path) if os.path.isfile(d.path) else 0)
 s.add(FileVersion(company_id=d.company_id,document_id=d.id,version=1,filename=d.filename,path=d.path,size=sz,mime=d.mime,sha256=d.sha256,uploaded_by=d.owner_id,created_at=d.created_at));s.flush()

def _view(d,versions=None):
 v={k:val for k,val in obj(d).items() if k!='path'}
 if versions is not None: v['versions']=[{k:val for k,val in obj(x).items() if k!='path'} for x in versions]
 return v

def _name(f): return re.sub(r'[\x00-\x1f\x7f]','',os.path.basename(f or 'file'))[:200] or 'file'

def _owner_or_manager(ctx,d):
 if not (has_all(ctx[2]) or d.owner_id==ctx[0].id): raise HTTPException(403,'فقط سازنده‌ی فایل یا مدیر مجاز است')

async def upload_document(entity: str, entity_id: int, restricted: bool, note: str, file: UploadFile, ctx, s: Session):
 u,cid,r=ctx
 if entity not in ENT: raise HTTPException(400,'نوع رکورد برای پیوست نامعتبر است')
 if not can_access(s,ctx,entity,entity_id): raise HTTPException(404,'رکورد یافت نشد')
 data=await file.read(MAX_UPLOAD+1);st=store_bytes(cid,data,MAX_UPLOAD)
 d=Document(company_id=cid,entity=entity,entity_id=entity_id,filename=_name(file.filename),path=st['path'],owner_id=u.id,size=st['size'],mime=st['mime'],sha256=st['sha256'],restricted=restricted,current_version=1);s.add(d);s.flush()
 s.add(FileVersion(company_id=cid,document_id=d.id,version=1,filename=d.filename,path=st['path'],size=st['size'],mime=st['mime'],sha256=st['sha256'],note=note,uploaded_by=u.id))
 audit(s,cid,u.id,'upload','document',d.id,{'entity':entity,'entity_id':entity_id,'size':st['size'],'sha256':st['sha256'],'restricted':restricted});s.commit();s.refresh(d);return _view(d)

async def upload_version(did: int, note: str, file: UploadFile, ctx, s: Session):
 u,cid,r=ctx;d=s.get(Document,did,with_for_update=True)
 if not d or not visible(s,ctx,d): raise HTTPException(404,'فایل یافت نشد')
 if d.restricted: _owner_or_manager(ctx,d)
 ensure_v1(s,d);data=await file.read(MAX_UPLOAD+1);st=store_bytes(cid,data,MAX_UPLOAD)
 n=(s.scalar(select(func.max(FileVersion.version)).where(FileVersion.document_id==d.id)) or 0)+1
 s.add(FileVersion(company_id=cid,document_id=d.id,version=n,filename=_name(file.filename),path=st['path'],size=st['size'],mime=st['mime'],sha256=st['sha256'],note=note,uploaded_by=u.id))
 d.path=st['path'];d.filename=_name(file.filename);d.size=st['size'];d.mime=st['mime'];d.sha256=st['sha256'];d.current_version=n
 audit(s,cid,u.id,'new_version','document',d.id,{'version':n,'size':st['size'],'sha256':st['sha256']});s.commit();s.refresh(d);return _view(d)

def documents(entity: Optional[str], entity_id: Optional[int], q: Optional[str], ctx, s: Session):
 u,cid,r=ctx;sel=select(Document).where(Document.company_id==cid,Document.deleted_at==None)
 if entity: sel=sel.where(Document.entity==entity)
 if entity_id: sel=sel.where(Document.entity_id==entity_id)
 if q: sel=sel.where(Document.filename.ilike('%'+q.replace('%','').replace('_','')+'%'))
 cache={};out=[]
 for d in s.scalars(sel.order_by(Document.id.desc()).limit(500)):
  if visible(s,ctx,d,cache): out.append(_view(d))
 return out

def document_detail(did: int, ctx, s: Session):
 d=s.get(Document,did)
 if not d or not visible(s,ctx,d): raise HTTPException(404,'فایل یافت نشد')
 ensure_v1(s,d);s.commit()
 return _view(d,s.scalars(select(FileVersion).where(FileVersion.document_id==d.id).order_by(FileVersion.version.desc())).all())

def download_document(did: int, version: Optional[int], ctx, s: Session):
 u,cid,r=ctx;d=s.get(Document,did)
 if not d or not visible(s,ctx,d): raise HTTPException(404,'فایل یافت نشد')
 ensure_v1(s,d)
 v=s.scalar(select(FileVersion).where(FileVersion.document_id==d.id,FileVersion.version==(version or d.current_version)))
 if not v or not os.path.isfile(v.path): raise HTTPException(404,'فایل یافت نشد')
 if d.restricted: audit(s,cid,u.id,'download','document',d.id,{'version':v.version})
 s.commit()
 return FileResponse(v.path,media_type=v.mime or 'application/octet-stream',filename=v.filename,headers={'X-Content-Type-Options':'nosniff'})

def document_patch(did: int, x: DocPatch, ctx, s: Session):
 u,cid,r=ctx;d=s.get(Document,did)
 if not d or not visible(s,ctx,d): raise HTTPException(404,'فایل یافت نشد')
 _owner_or_manager(ctx,d);d.restricted=x.restricted;audit(s,cid,u.id,'acl','document',d.id,{'restricted':x.restricted});s.commit();return _view(d)

def document_delete(did: int, ctx, s: Session):
 """حذف نرم: فایل‌ها و نسخه‌ها روی دیسک می‌مانند (پیوست‌ها ممکن است مستند مالی باشند)"""
 u,cid,r=ctx;d=s.get(Document,did)
 if not d or not visible(s,ctx,d): raise HTTPException(404,'فایل یافت نشد')
 _owner_or_manager(ctx,d);d.deleted_at=utcnow();audit(s,cid,u.id,'delete','document',d.id);s.commit();return {'ok':True}
