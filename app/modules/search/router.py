from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .schemas import AdvIn, SavedIn
from .service import search_schema as _s_search_schema, search_global as _s_search_global, search_advanced as _s_search_advanced, saved_list as _s_saved_list, saved_save as _s_saved_save, saved_delete as _s_saved_delete, search_status as _s_search_status

router=APIRouter()

@router.get('/api/search/schema')
def search_schema(ctx=Depends(current)):
 return _s_search_schema(ctx=ctx)

@router.get('/api/search/global')
def search_global(q: str=Query(..., min_length=1, max_length=200), types: Optional[str]=Query(None, max_length=200), limit: int=Query(5, ge=1, le=20), ctx=Depends(current), s: Session=Depends(db)):
 return _s_search_global(q=q, types=types, limit=limit, ctx=ctx, s=s)

@router.post('/api/search/advanced')
def search_advanced(x: AdvIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_search_advanced(x=x, ctx=ctx, s=s)

@router.get('/api/search/saved')
def saved_list(entity: Optional[str]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_saved_list(entity=entity, ctx=ctx, s=s)

@router.post('/api/search/saved')
def saved_save(x: SavedIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_saved_save(x=x, ctx=ctx, s=s)

@router.delete('/api/search/saved/{fid}')
def saved_delete(fid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_saved_delete(fid=fid, ctx=ctx, s=s)

@router.get('/api/search/status')
def search_status(ctx=Depends(current), s: Session=Depends(db)):
 'وضعیت ایندکس pg_trgm (فقط مدیر). اگر ناقص باشد، دستور SQL لازم برای DBA برگردانده می\u200cشود؛ هر بار راه\u200cاندازی/مایگریشن دوباره تلاش می\u200cکند.'
 return _s_search_status(ctx=ctx, s=s)
