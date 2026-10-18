from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .schemas import ContractIn, ContractPatch
from .service import contracts as _s_contracts, contract_create as _s_contract_create, contract_get as _s_contract_get, contract_patch as _s_contract_patch

router=APIRouter()

@router.get('/api/contracts')
def contracts(status: Optional[str]=None, customer_id: Optional[int]=None, supplier_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_contracts(status=status, customer_id=customer_id, supplier_id=supplier_id, ctx=ctx, s=s)

@router.post('/api/contracts')
def contract_create(x: ContractIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_contract_create(x=x, ctx=ctx, s=s)

@router.get('/api/contracts/{cid_}')
def contract_get(cid_: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_contract_get(cid_=cid_, ctx=ctx, s=s)

@router.patch('/api/contracts/{cid_}')
def contract_patch(cid_: int, x: ContractPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_contract_patch(cid_=cid_, x=x, ctx=ctx, s=s)
