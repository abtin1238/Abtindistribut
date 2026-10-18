from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.schemas import InvoiceNoteIn, OrderIn, ReturnIn
from .service import create_order as _s_create_order, approve_order as _s_approve_order, orders as _s_orders, invoices as _s_invoices, invoice_note as _s_invoice_note, invoice_detail as _s_invoice_detail, invoice_pdf as _s_invoice_pdf, report_sales as _s_report_sales, cancel_order as _s_cancel_order, return_order as _s_return_order, sales_returns as _s_sales_returns

router=APIRouter()

@router.post('/api/orders')
def create_order(x: OrderIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_order(x=x, ctx=ctx, s=s)

@router.post('/api/orders/{oid}/approve')
def approve_order(oid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_approve_order(oid=oid, ctx=ctx, s=s)

@router.get('/api/orders')
def orders(response: Response, limit: int=Query(500, ge=1, le=1000), offset: int=Query(0, ge=0), ctx=Depends(current), s: Session=Depends(db)):
 return _s_orders(response=response, limit=limit, offset=offset, ctx=ctx, s=s)

@router.get('/api/invoices')
def invoices(status: str=Query(default=''), q: str=Query(default='', max_length=100), start: date | None=Query(default=None), end: date | None=Query(default=None), limit: int=Query(default=500, ge=1, le=1000), ctx=Depends(current), s: Session=Depends(db)):
 return _s_invoices(status=status, q=q, start=start, end=end, limit=limit, ctx=ctx, s=s)

@router.patch('/api/invoices/{iid}/note')
def invoice_note(iid: int, x: InvoiceNoteIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_invoice_note(iid=iid, x=x, ctx=ctx, s=s)

@router.get('/api/invoices/{iid}')
def invoice_detail(iid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_invoice_detail(iid=iid, ctx=ctx, s=s)

@router.get('/api/invoices/{iid}/pdf')
def invoice_pdf(iid: int, ctx=Depends(current), s: Session=Depends(db)):
 data,number=_s_invoice_pdf(iid=iid, ctx=ctx, s=s)
 return Response(content=data, media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="invoice-{number}.pdf"', 'Cache-Control': 'no-store'})

@router.get('/api/reports/sales')
def report_sales(start: date=Query(default=date.today()), end: date=Query(default=date.today()), ctx=Depends(current), s: Session=Depends(db)):
 return _s_report_sales(start=start, end=end, ctx=ctx, s=s)

@router.post('/api/orders/{oid}/cancel')
def cancel_order(oid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_cancel_order(oid=oid, ctx=ctx, s=s)

@router.post('/api/orders/{oid}/return')
def return_order(oid: int, x: ReturnIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_return_order(oid=oid, x=x, ctx=ctx, s=s)

@router.get('/api/sales-returns')
def sales_returns(ctx=Depends(current), s: Session=Depends(db)):
 return _s_sales_returns(ctx=ctx, s=s)
