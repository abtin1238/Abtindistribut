from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.common import audit, obj
from app.core.paging import page_rows
from app.core.security import branch_clause, need
from app.models import Branch, Customer, Membership, CustomerAddress, CustomerContact
from app.services.accounting import party_balance, party_balances
from .schemas import AddressIn, AddressPatch, ContactIn, ContactPatch, CustomerIn, CustomerPatch

def customers(response: Response, limit: int, offset: int, ctx, s: Session):
 b=party_balances(s,ctx[1],'customer');st=select(Customer).where(Customer.company_id==ctx[1]).order_by(Customer.id);cl=branch_clause(Customer.branch_id,ctx[0],ctx[1],ctx[2])
 if cl is not None: st=st.where(cl)
 return [{**obj(x),'balance':b.get(x.id,Decimal(0))} for x in page_rows(s,st,response,limit,offset)]

def add_customer(x: CustomerIn, ctx, s: Session):
 u,cid,r=ctx; need(ctx,'crm.write'); d=x.model_dump()
 mine=[m for m in s.scalars(select(Membership.branch_id).where(Membership.user_id==u.id,Membership.company_id==cid)) if m is not None]
 if d.get('branch_id') is not None:
  b=s.get(Branch,d['branch_id'])
  if not b or b.company_id!=cid: raise HTTPException(404,'شعبه یافت نشد')
 if branch_clause(Customer.branch_id,u,cid,r) is not None:
  if not mine: raise HTTPException(400,'مدیر باید به یک شعبه متصل باشد')
  if d.get('branch_id') not in mine: d['branch_id']=mine[0]
 q=Customer(company_id=cid,**d);s.add(q);audit(s,cid,u.id,'create','customer',None,x.model_dump());s.commit();s.refresh(q);return obj(q)

def update_customer(customer_id: int, x: CustomerPatch, ctx, s: Session):
 """ویرایش مشتری. مدیر محدود به شعبه فقط مشتریان شعبه‌ی خودش را می‌بیند و نمی‌تواند مشتری را به شعبه‌ی دیگر ببرد یا بی‌شعبه کند."""
 u,cid,r=ctx; need(ctx,'crm.write'); c=_cust(s,cid,customer_id,ctx); d=x.model_dump(exclude_unset=True)
 if not d: raise HTTPException(400,'تغییری ارسال نشده است')
 for k in ('name',):
  if k in d and d[k] is None: raise HTTPException(400,'نام نمی‌تواند خالی باشد')
 if 'branch_id' in d:
  if d['branch_id'] is not None:
   b=s.get(Branch,d['branch_id'])
   if not b or b.company_id!=cid: raise HTTPException(404,'شعبه یافت نشد')
  if branch_clause(Customer.branch_id,u,cid,r) is not None:
   mine=[m for m in s.scalars(select(Membership.branch_id).where(Membership.user_id==u.id,Membership.company_id==cid)) if m is not None]
   if d['branch_id'] not in mine: raise HTTPException(403,'شعبه خارج از محدوده‌ی شما است')
 old={k:getattr(c,k) for k in d}
 for k,v in d.items(): setattr(c,k,v)
 audit(s,cid,u.id,'update','customer',c.id,{'old':{k:str(v) for k,v in old.items()},'new':{k:str(v) for k,v in d.items()}});s.commit();s.refresh(c);return obj(c)

def _cust(s,cid,customer_id,ctx=None):
 c=s.get(Customer,customer_id)
 if not c or c.company_id!=cid: raise HTTPException(404,'مشتری یافت نشد')
 cl=branch_clause(Customer.branch_id,ctx[0],cid,ctx[2]) if ctx else None
 if cl is not None and not s.scalar(select(Customer.id).where(Customer.id==c.id,cl)): raise HTTPException(404,'مشتری یافت نشد')
 return c
def _sync_default(s,c):
 """آدرس/موقعیت پیش‌فرض را روی فیلدهای قدیمی مشتری (address/region/lat/lng) منعکس می‌کند تا نقشه و گزارش‌های موجود سالم بمانند."""
 d=s.scalar(select(CustomerAddress).where(CustomerAddress.customer_id==c.id,CustomerAddress.is_default==True,CustomerAddress.active==True))
 if d: c.address=d.address;c.region=d.region;c.lat=d.lat;c.lng=d.lng
def _make_default(s,a):
 s.execute(update(CustomerAddress).where(CustomerAddress.customer_id==a.customer_id,CustomerAddress.id!=a.id).values(is_default=False));a.is_default=True

def customer_detail(customer_id: int, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx);bal=party_balance(s,cid,'customer',c.id)
 return {**obj(c),'balance':bal,'addresses':addresses(customer_id,ctx,s),'contacts':contacts(customer_id,ctx,s)}

def addresses(customer_id: int, ctx, s: Session, include_inactive: bool=False):
 u,cid,r=ctx;_cust(s,cid,customer_id,ctx);q=select(CustomerAddress).where(CustomerAddress.customer_id==customer_id,CustomerAddress.company_id==cid)
 if not include_inactive: q=q.where(CustomerAddress.active==True)
 return [obj(a) for a in s.scalars(q.order_by(CustomerAddress.is_default.desc(),CustomerAddress.id)).all()]

def add_address(customer_id: int, x: AddressIn, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx)
 has=s.scalar(select(CustomerAddress.id).where(CustomerAddress.customer_id==c.id,CustomerAddress.active==True,CustomerAddress.is_default==True))
 a=CustomerAddress(company_id=cid,customer_id=c.id,**{**x.model_dump(),'is_default':False});s.add(a);s.flush()
 if x.is_default or not has: _make_default(s,a)
 _sync_default(s,c);audit(s,cid,u.id,'create','customer_address',a.id,{'customer_id':c.id,**x.model_dump()});s.commit();s.refresh(a);return obj(a)

def patch_address(customer_id: int, aid: int, x: AddressPatch, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx);a=s.get(CustomerAddress,aid,with_for_update=True)
 if not a or a.company_id!=cid or a.customer_id!=c.id or not a.active: raise HTTPException(404,'آدرس یافت نشد')
 d=x.model_dump(exclude_unset=True);dflt=d.pop('is_default',None)
 for k,v in d.items():
  if v is None and k in ('title','kind','address','region'): continue
  setattr(a,k,v)
 if dflt is True: _make_default(s,a)
 elif dflt is False and a.is_default: raise HTTPException(409,'برای تغییر آدرس پیش‌فرض، آدرس دیگری را پیش‌فرض کنید')
 _sync_default(s,c);audit(s,cid,u.id,'update','customer_address',a.id,x.model_dump(exclude_unset=True));s.commit();s.refresh(a);return obj(a)

def delete_address(customer_id: int, aid: int, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx);a=s.get(CustomerAddress,aid,with_for_update=True)
 if not a or a.company_id!=cid or a.customer_id!=c.id or not a.active: raise HTTPException(404,'آدرس یافت نشد')
 if a.is_default and s.scalar(select(CustomerAddress.id).where(CustomerAddress.customer_id==c.id,CustomerAddress.active==True,CustomerAddress.id!=a.id)): raise HTTPException(409,'آدرس پیش‌فرض را نمی‌توان حذف کرد؛ ابتدا آدرس دیگری را پیش‌فرض کنید')
 a.active=False;a.is_default=False;audit(s,cid,u.id,'delete','customer_address',a.id);s.commit();return {'id':a.id,'active':False}

def contacts(customer_id: int, ctx, s: Session):
 u,cid,r=ctx;_cust(s,cid,customer_id,ctx)
 return [obj(x) for x in s.scalars(select(CustomerContact).where(CustomerContact.customer_id==customer_id,CustomerContact.company_id==cid,CustomerContact.active==True).order_by(CustomerContact.is_primary.desc(),CustomerContact.id)).all()]

def _make_primary(s,k):
 s.execute(update(CustomerContact).where(CustomerContact.customer_id==k.customer_id,CustomerContact.id!=k.id).values(is_primary=False));k.is_primary=True

def add_contact(customer_id: int, x: ContactIn, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx)
 has=s.scalar(select(CustomerContact.id).where(CustomerContact.customer_id==c.id,CustomerContact.active==True,CustomerContact.is_primary==True))
 k=CustomerContact(company_id=cid,customer_id=c.id,**{**x.model_dump(),'is_primary':False});s.add(k);s.flush()
 if x.is_primary or not has: _make_primary(s,k)
 audit(s,cid,u.id,'create','customer_contact',k.id,{'customer_id':c.id,**x.model_dump()});s.commit();s.refresh(k);return obj(k)

def patch_contact(customer_id: int, kid: int, x: ContactPatch, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx);k=s.get(CustomerContact,kid,with_for_update=True)
 if not k or k.company_id!=cid or k.customer_id!=c.id or not k.active: raise HTTPException(404,'مخاطب یافت نشد')
 d=x.model_dump(exclude_unset=True);prim=d.pop('is_primary',None)
 for kk,v in d.items():
  if v is None and kk=='name': continue
  setattr(k,kk,v if v is not None else '')
 if prim is True: _make_primary(s,k)
 elif prim is False and k.is_primary: raise HTTPException(409,'برای تغییر مخاطب اصلی، مخاطب دیگری را اصلی کنید')
 audit(s,cid,u.id,'update','customer_contact',k.id,x.model_dump(exclude_unset=True));s.commit();s.refresh(k);return obj(k)

def delete_contact(customer_id: int, kid: int, ctx, s: Session):
 u,cid,r=ctx;c=_cust(s,cid,customer_id,ctx);k=s.get(CustomerContact,kid,with_for_update=True)
 if not k or k.company_id!=cid or k.customer_id!=c.id or not k.active: raise HTTPException(404,'مخاطب یافت نشد')
 k.active=False;was=k.is_primary;k.is_primary=False
 if was:
  nxt=s.scalar(select(CustomerContact).where(CustomerContact.customer_id==c.id,CustomerContact.active==True,CustomerContact.id!=k.id).order_by(CustomerContact.id))
  if nxt: nxt.is_primary=True
 audit(s,cid,u.id,'delete','customer_contact',k.id);s.commit();return {'id':k.id,'active':False}
