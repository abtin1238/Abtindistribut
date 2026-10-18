from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import CountApproveIn, CountIn, CountLinesIn, LocationIn, StockIn, TransferIn, WarehouseIn
from . import stockops as ops
from .service import warehouses as _s_warehouses, add_warehouse as _s_add_warehouse, stock as _s_stock, adjust_stock as _s_adjust_stock, create_transfer as _s_create_transfer, receive_transfer as _s_receive_transfer, cancel_transfer as _s_cancel_transfer, list_transfers as _s_list_transfers, report_stock as _s_report_stock

router=APIRouter()

@router.get('/api/warehouses')
def warehouses(ctx=Depends(current), s: Session=Depends(db)):
 return _s_warehouses(ctx=ctx, s=s)

@router.post('/api/warehouses')
def add_warehouse(x: WarehouseIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_warehouse(x=x, ctx=ctx, s=s)

@router.get('/api/stock')
def stock(ctx=Depends(current), s: Session=Depends(db)):
 return _s_stock(ctx=ctx, s=s)

@router.post('/api/stock/adjust')
def adjust_stock(x: StockIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_adjust_stock(x=x, ctx=ctx, s=s)

@router.post('/api/stock/transfers')
def create_transfer(x: TransferIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_transfer(x=x, ctx=ctx, s=s)

@router.post('/api/stock/transfers/{tid}/receive')
def receive_transfer(tid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_receive_transfer(tid=tid, ctx=ctx, s=s)

@router.post('/api/stock/transfers/{tid}/cancel')
def cancel_transfer(tid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_cancel_transfer(tid=tid, ctx=ctx, s=s)

@router.get('/api/stock/transfers')
def list_transfers(ctx=Depends(current), s: Session=Depends(db)):
 return _s_list_transfers(ctx=ctx, s=s)

@router.get('/api/reports/stock')
def report_stock(warehouse_id: Optional[int]=Query(None), ctx=Depends(current), s: Session=Depends(db)):
 return _s_report_stock(warehouse_id=warehouse_id, ctx=ctx, s=s)

@router.patch('/api/stock/{sid}')
def set_location(sid: int, x: LocationIn, ctx=Depends(current), s: Session=Depends(db)):
 return ops.set_location(sid=sid, x=x, ctx=ctx, s=s)

@router.get('/api/stock/moves')
def stock_moves(response: Response, limit: int=Query(100,ge=1,le=1000), offset: int=Query(0,ge=0), warehouse_id: Optional[int]=None, product_id: Optional[int]=None, kind: Optional[str]=None, start: Optional[date]=None, end: Optional[date]=None, ctx=Depends(current), s: Session=Depends(db)):
 return ops.moves(response, limit, offset, warehouse_id, product_id, kind, start, end, ctx, s)

@router.get('/api/stock/kardex')
def stock_kardex(product_id: int, warehouse_id: Optional[int]=None, start: Optional[date]=None, end: Optional[date]=None, ctx=Depends(current), s: Session=Depends(db)):
 return ops.kardex(product_id, warehouse_id, start, end, ctx, s)

@router.get('/api/stock/batches')
def stock_batches(warehouse_id: Optional[int]=None, product_id: Optional[int]=None, include_empty: bool=False, ctx=Depends(current), s: Session=Depends(db)):
 return ops.batches(warehouse_id, product_id, include_empty, ctx, s)

@router.get('/api/stock/expiring')
def stock_expiring(days: int=Query(30,ge=0,le=3650), warehouse_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return ops.expiring(days, warehouse_id, ctx, s)

@router.get('/api/reports/stock-valuation')
def stock_valuation(warehouse_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return ops.valuation(warehouse_id, ctx, s)

@router.get('/api/stock/counts')
def stock_counts(ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_list(ctx, s)

@router.post('/api/stock/counts')
def stock_count_create(x: CountIn, ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_create(x, ctx, s)

@router.get('/api/stock/counts/{cid}')
def stock_count_get(cid: int, ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_get(cid, ctx, s)

@router.put('/api/stock/counts/{cid}/lines')
def stock_count_lines(cid: int, x: CountLinesIn, ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_set_lines(cid, x, ctx, s)

@router.post('/api/stock/counts/{cid}/approve')
def stock_count_approve(cid: int, x: CountApproveIn, ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_approve(cid, x, ctx, s)

@router.post('/api/stock/counts/{cid}/cancel')
def stock_count_cancel(cid: int, ctx=Depends(current), s: Session=Depends(db)):
 return ops.count_cancel(cid, ctx, s)
