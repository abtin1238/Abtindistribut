from __future__ import annotations
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from .service import import_entities as _s_import_entities, import_preview as _s_import_preview, import_commit as _s_import_commit

router=APIRouter()

@router.get('/api/import/entities')
def import_entities(ctx=Depends(current)):
 return _s_import_entities(ctx=ctx)

@router.post('/api/import/preview')
def import_preview(file: UploadFile=File(...), entity: str=Form(''), mapping: str=Form(''), sheet: str=Form(''), header_row: Optional[int]=Form(None), warehouse_id: Optional[int]=Form(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_import_preview(file=file, entity=entity, mapping=mapping, sheet=sheet, header_row=header_row, warehouse_id=warehouse_id, ctx=ctx, s=s)

@router.post('/api/import/commit')
def import_commit(file: UploadFile=File(...), entity: str=Form(''), mapping: str=Form(''), sheet: str=Form(''), header_row: Optional[int]=Form(None), warehouse_id: Optional[int]=Form(None), strict: bool=Form(False), ctx=Depends(current), s: Session=Depends(db)):
 return _s_import_commit(file=file, entity=entity, mapping=mapping, sheet=sheet, header_row=header_row, warehouse_id=warehouse_id, strict=strict, ctx=ctx, s=s)
