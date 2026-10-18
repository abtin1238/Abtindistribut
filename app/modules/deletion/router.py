from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .service import REGISTRY, keys as _s_keys, remove as _s_remove, remove_role as _s_remove_role, remove_user as _s_remove_user

router=APIRouter()

@router.get('/api/deletable')
def deletable(ctx=Depends(current)):
 'فهرست بخش‌هایی که مدیر کل می‌تواند ردیفشان را حذف کند'
 return _s_keys(ctx)

@router.delete('/api/users/{uid}')
def delete_user(uid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_remove_user(uid=uid, ctx=ctx, s=s)

@router.delete('/api/roles/{rid}')
def delete_role(rid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_remove_role(rid=rid, ctx=ctx, s=s)

def _mk(key):
 def h(rid: int, ctx=Depends(current), s: Session=Depends(db)): return _s_remove(key=key, rid=rid, ctx=ctx, s=s)
 h.__name__='delete_'+key.replace('/','_').replace('-','_')
 return h

for _k in REGISTRY: router.add_api_route(f'/api/{_k}/{{rid}}',_mk(_k),methods=['DELETE'])
