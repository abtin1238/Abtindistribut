from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from datetime import date
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import utcnow
from app.core.database import Base

class Supplier(Base):
 __tablename__='suppliers'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(200)); phone:Mapped[str]=mapped_column(String(50),default=''); balance:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0)

class Purchase(Base):
 __tablename__='purchases'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); number:Mapped[str]=mapped_column(String(80),unique=True); supplier_id:Mapped[int]=mapped_column(ForeignKey('suppliers.id')); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); status:Mapped[str]=mapped_column(String(30),default='draft'); total:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); discount:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); freight:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); received_value:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class PurchaseItem(Base):
 __tablename__='purchase_items'; id:Mapped[int]=mapped_column(primary_key=True); purchase_id:Mapped[int]=mapped_column(ForeignKey('purchases.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); unit_cost:Mapped[Decimal]=mapped_column(Numeric(18,2)); discount:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); landed:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); returned_qty:Mapped[Decimal]=mapped_column(Numeric(18,3),default=0,server_default='0'); received_qty:Mapped[Decimal]=mapped_column(Numeric(18,3),default=0,server_default='0'); batch_no:Mapped[str]=mapped_column(String(60),default='',server_default=''); expiry_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True)

class CostAllocation(Base):
    """هزینهٔ جانبی جداگانهٔ یک خرید (گمرک/حمل/بیمه…) که پیش از رسید روی اقلام تسهیم شده است."""
    __tablename__='cost_allocations'
    id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); purchase_id:Mapped[int]=mapped_column(ForeignKey('purchases.id'),index=True); label:Mapped[str]=mapped_column(String(100)); basis:Mapped[str]=mapped_column(String(10),default='value'); amount:Mapped[Decimal]=mapped_column(Numeric(18,2)); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
