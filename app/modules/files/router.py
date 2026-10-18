from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from .schemas import DocPatch
from .service import upload_document as _s_upload_document, upload_version as _s_upload_version, documents as _s_documents, document_detail as _s_document_detail, download_document as _s_download_document, document_patch as _s_document_patch, document_delete as _s_document_delete

router=APIRouter()

@router.post('/api/documents/upload')
async def upload_document(entity: str, entity_id: int, restricted: bool=False, note: str=Query('', max_length=300), file: UploadFile=File(...), ctx=Depends(current), s: Session=Depends(db)):
 return await _s_upload_document(entity=entity, entity_id=entity_id, restricted=restricted, note=note, file=file, ctx=ctx, s=s)

@router.post('/api/documents/{did}/versions')
async def upload_version(did: int, note: str=Query('', max_length=300), file: UploadFile=File(...), ctx=Depends(current), s: Session=Depends(db)):
 return await _s_upload_version(did=did, note=note, file=file, ctx=ctx, s=s)

@router.get('/api/documents')
def documents(entity: Optional[str]=None, entity_id: Optional[int]=None, q: Optional[str]=Query(None, max_length=100), ctx=Depends(current), s: Session=Depends(db)):
 return _s_documents(entity=entity, entity_id=entity_id, q=q, ctx=ctx, s=s)

@router.get('/api/documents/{did}')
def document_detail(did: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_document_detail(did=did, ctx=ctx, s=s)

@router.get('/api/documents/{did}/download')
def download_document(did: int, version: Optional[int]=Query(None, ge=1), ctx=Depends(current), s: Session=Depends(db)):
 return _s_download_document(did=did, version=version, ctx=ctx, s=s)

@router.patch('/api/documents/{did}')
def document_patch(did: int, x: DocPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_document_patch(did=did, x=x, ctx=ctx, s=s)

@router.delete('/api/documents/{did}')
def document_delete(did: int, ctx=Depends(current), s: Session=Depends(db)):
 'حذف نرم: فایل\u200cها و نسخه\u200cها روی دیسک می\u200cمانند (پیوست\u200cها ممکن است مستند مالی باشند)'
 return _s_document_delete(did=did, ctx=ctx, s=s)
