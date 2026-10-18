from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.modules.crm.schemas import AddressIn, AddressPatch, ContactIn, ContactPatch, CustomerPatch
from app.schemas import CustomerIn
from .service import customers as _s_customers, add_customer as _s_add_customer, update_customer as _s_update_customer, customer_detail as _s_detail, addresses as _s_addr, add_address as _s_add_addr, patch_address as _s_patch_addr, delete_address as _s_del_addr, contacts as _s_cont, add_contact as _s_add_cont, patch_contact as _s_patch_cont, delete_contact as _s_del_cont

router=APIRouter()

@router.get('/api/customers')
def customers(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_customers(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.post('/api/customers')
def add_customer(x: CustomerIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_customer(x=x, ctx=ctx, s=s)

@router.patch('/api/customers/{customer_id}')
def update_customer(customer_id: int, x: CustomerPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_update_customer(customer_id=customer_id, x=x, ctx=ctx, s=s)

@router.get('/api/customers/{customer_id}')
def customer_detail(customer_id: int, ctx=Depends(current), s: Session=Depends(db)):
 'جزئیات مشتری + آدرس‌ها + مخاطبین + مانده (از دفتر)'
 return _s_detail(customer_id=customer_id, ctx=ctx, s=s)

@router.get('/api/customers/{customer_id}/addresses')
def list_addresses(customer_id: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_addr(customer_id=customer_id, ctx=ctx, s=s)

@router.post('/api/customers/{customer_id}/addresses')
def add_address(customer_id: int, x: AddressIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_addr(customer_id=customer_id, x=x, ctx=ctx, s=s)

@router.patch('/api/customers/{customer_id}/addresses/{aid}')
def patch_address(customer_id: int, aid: int, x: AddressPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_patch_addr(customer_id=customer_id, aid=aid, x=x, ctx=ctx, s=s)

@router.delete('/api/customers/{customer_id}/addresses/{aid}')
def delete_address(customer_id: int, aid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_del_addr(customer_id=customer_id, aid=aid, ctx=ctx, s=s)

@router.get('/api/customers/{customer_id}/contacts')
def list_contacts(customer_id: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_cont(customer_id=customer_id, ctx=ctx, s=s)

@router.post('/api/customers/{customer_id}/contacts')
def add_contact(customer_id: int, x: ContactIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_cont(customer_id=customer_id, x=x, ctx=ctx, s=s)

@router.patch('/api/customers/{customer_id}/contacts/{kid}')
def patch_contact(customer_id: int, kid: int, x: ContactPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_patch_cont(customer_id=customer_id, kid=kid, x=x, ctx=ctx, s=s)

@router.delete('/api/customers/{customer_id}/contacts/{kid}')
def delete_contact(customer_id: int, kid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_del_cont(customer_id=customer_id, kid=kid, ctx=ctx, s=s)
