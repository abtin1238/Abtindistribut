from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import utcnow
from app.core.database import Base

class Order(Base):
 __tablename__='orders'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); number:Mapped[str]=mapped_column(String(80),unique=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id')); seller_id:Mapped[int]=mapped_column(ForeignKey('users.id')); warehouse_id:Mapped[int]=mapped_column(ForeignKey('warehouses.id')); status:Mapped[str]=mapped_column(String(30),default='draft'); total:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); shipping:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); note:Mapped[str]=mapped_column(Text,default='',server_default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class OrderItem(Base):
 __tablename__='order_items'; id:Mapped[int]=mapped_column(primary_key=True); order_id:Mapped[int]=mapped_column(ForeignKey('orders.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); unit_price:Mapped[Decimal]=mapped_column(Numeric(18,2)); discount:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0)

class Invoice(Base):
 __tablename__='invoices'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); order_id:Mapped[int]=mapped_column(ForeignKey('orders.id')); number:Mapped[str]=mapped_column(String(80),unique=True); subtotal:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); tax:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); shipping:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); total:Mapped[Decimal]=mapped_column(Numeric(18,2)); paid:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); returned:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); status:Mapped[str]=mapped_column(String(30),default='open'); note:Mapped[str]=mapped_column(Text,default='',server_default=''); terms:Mapped[str]=mapped_column(Text,default='',server_default=''); issued_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class InvoiceLine(Base):
 __tablename__='invoice_lines'; id:Mapped[int]=mapped_column(primary_key=True); invoice_id:Mapped[int]=mapped_column(ForeignKey('invoices.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); description:Mapped[str]=mapped_column(String(250),default=''); unit:Mapped[str]=mapped_column(String(30),default=''); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); unit_price:Mapped[Decimal]=mapped_column(Numeric(18,2)); discount:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); line_total:Mapped[Decimal]=mapped_column(Numeric(18,2)); unit_cost:Mapped[Decimal]=mapped_column(Numeric(18,4),default=0,server_default='0'); cogs:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0')

class SalesReturn(Base):
 __tablename__='sales_returns'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); number:Mapped[str]=mapped_column(String(80),unique=True); order_id:Mapped[int]=mapped_column(ForeignKey('orders.id')); invoice_id:Mapped[int]=mapped_column(ForeignKey('invoices.id'),index=True); subtotal:Mapped[Decimal]=mapped_column(Numeric(18,2)); tax:Mapped[Decimal]=mapped_column(Numeric(18,2)); total:Mapped[Decimal]=mapped_column(Numeric(18,2)); reason:Mapped[str]=mapped_column(Text,default=''); restocked:Mapped[bool]=mapped_column(Boolean,default=True); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class SalesReturnLine(Base):
 __tablename__='sales_return_lines'; id:Mapped[int]=mapped_column(primary_key=True); return_id:Mapped[int]=mapped_column(ForeignKey('sales_returns.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); amount:Mapped[Decimal]=mapped_column(Numeric(18,2))
