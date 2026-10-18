from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Customer(Base):
 __tablename__='customers'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); code:Mapped[str]=mapped_column(String(60)); name:Mapped[str]=mapped_column(String(200)); phone:Mapped[str]=mapped_column(String(50),default=''); address:Mapped[str]=mapped_column(Text,default=''); region:Mapped[str]=mapped_column(String(120),default=''); credit_limit:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); balance:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); customer_group:Mapped[str]=mapped_column(String(100),default='',server_default=''); lat:Mapped[Optional[float]]=mapped_column(); lng:Mapped[Optional[float]]=mapped_column(); active:Mapped[bool]=mapped_column(Boolean,default=True); branch_id:Mapped[Optional[int]]=mapped_column(ForeignKey('branches.id'),default=None)

class CustomerAddress(Base):
 """آدرس‌های چندگانهٔ مشتری (تحویل/صورت‌حساب/…)؛ فقط یک آدرس پیش‌فرض فعال؛ حذف = غیرفعال‌سازی."""
 __tablename__='customer_addresses'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True); title:Mapped[str]=mapped_column(String(100)); kind:Mapped[str]=mapped_column(String(20),default='delivery',server_default='delivery'); address:Mapped[str]=mapped_column(Text,default=''); region:Mapped[str]=mapped_column(String(120),default='',server_default=''); lat:Mapped[Optional[float]]=mapped_column(); lng:Mapped[Optional[float]]=mapped_column(); is_default:Mapped[bool]=mapped_column(Boolean,default=False); active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class CustomerContact(Base):
 """مخاطبین مشتری؛ حداکثر یک مخاطب اصلی فعال."""
 __tablename__='customer_contacts'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True); name:Mapped[str]=mapped_column(String(150)); role:Mapped[str]=mapped_column(String(100),default='',server_default=''); phone:Mapped[str]=mapped_column(String(50),default='',server_default=''); email:Mapped[str]=mapped_column(String(200),default='',server_default=''); is_primary:Mapped[bool]=mapped_column(Boolean,default=False); active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
