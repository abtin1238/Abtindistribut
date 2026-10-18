from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from datetime import date
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Warehouse(Base):
 __tablename__='warehouses'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); branch_id:Mapped[Optional[int]]=mapped_column(ForeignKey('branches.id')); name:Mapped[str]=mapped_column(String(200)); address:Mapped[str]=mapped_column(Text,default=''); active:Mapped[bool]=mapped_column(Boolean,default=True)

class Stock(Base):
 __tablename__='stock'; id:Mapped[int]=mapped_column(primary_key=True); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3),default=0); reserved:Mapped[Decimal]=mapped_column(Numeric(18,3),default=0); location:Mapped[str]=mapped_column(String(60),default='',server_default='')

class StockMove(Base):
 __tablename__='stock_moves'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); kind:Mapped[str]=mapped_column(String(30)); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); unit_cost:Mapped[Optional[Decimal]]=mapped_column(Numeric(18,4),nullable=True); reference:Mapped[str]=mapped_column(String(100),default=''); reason:Mapped[str]=mapped_column(String(200),default='',server_default=''); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class StockTransfer(Base):
 __tablename__='stock_transfers'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); number:Mapped[str]=mapped_column(String(80),unique=True); from_warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); to_warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); status:Mapped[str]=mapped_column(String(30),default='in_transit'); note:Mapped[str]=mapped_column(Text,default=''); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); received_by:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id')); received_at:Mapped[Optional[datetime]]=mapped_column(DateTime)

class StockBatch(Base):
 """بچ/لات کالا با تاریخ انقضا؛ جمع بچ‌ها ≤ موجودی ردیف Stock (مازاد = «بدون بچ»)"""
 __tablename__='stock_batches'; __table_args__=(UniqueConstraint('warehouse_id','product_id','batch_no'),Index('ix_batch_expiry','company_id','expiry_date'))
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); batch_no:Mapped[str]=mapped_column(String(60)); expiry_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3),default=0); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class StockCount(Base):
 """انبارگردانی: عکس لحظه‌ای موجودی ← شمارش ← تأیید (اختلاف‌ها تعدیل و سند می‌شوند)"""
 __tablename__='stock_counts'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); number:Mapped[str]=mapped_column(String(80),unique=True); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); status:Mapped[str]=mapped_column(String(20),default='draft'); note:Mapped[str]=mapped_column(Text,default=''); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); approved_by:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); approved_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True)

class StockCountLine(Base):
 __tablename__='stock_count_lines'; __table_args__=(UniqueConstraint('count_id','product_id'),)
 id:Mapped[int]=mapped_column(primary_key=True); count_id:Mapped[int]=mapped_column(ForeignKey('stock_counts.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); system_qty:Mapped[Decimal]=mapped_column(Numeric(18,3)); counted_qty:Mapped[Optional[Decimal]]=mapped_column(Numeric(18,3),nullable=True)

class StockTransferItem(Base):
 """اقلام یک برگهٔ انتقال (چندقلمی). انتقال‌های قدیمی بدون ردیف‌اند و از product_id/quantity سرتیتر خوانده می‌شوند."""
 __tablename__='stock_transfer_items'; __table_args__=(UniqueConstraint('transfer_id','product_id'),)
 id:Mapped[int]=mapped_column(primary_key=True); transfer_id:Mapped[int]=mapped_column(ForeignKey('stock_transfers.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3))

class StockTransferBatch(Base):
 """بچ‌های در راه یک انتقال (از مبدأ کم می‌شود؛ هنگام دریافت به مقصد یا هنگام لغو به مبدأ برمی‌گردد)"""
 __tablename__='stock_transfer_batches'; id:Mapped[int]=mapped_column(primary_key=True); transfer_id:Mapped[int]=mapped_column(ForeignKey('stock_transfers.id'),index=True); product_id:Mapped[Optional[int]]=mapped_column(ForeignKey('products.id'),nullable=True); batch_no:Mapped[str]=mapped_column(String(60)); expiry_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3))
