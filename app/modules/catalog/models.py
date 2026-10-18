from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy import false as sa_false
from app.core.database import Base

class Brand(Base):
 __tablename__='brands'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(150))

class Category(Base):
 __tablename__='categories'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(150)); parent_id:Mapped[Optional[int]]=mapped_column(ForeignKey('categories.id'))

class Product(Base):
 __tablename__='products'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); sku:Mapped[str]=mapped_column(String(80)); name:Mapped[str]=mapped_column(String(200)); brand_id:Mapped[Optional[int]]=mapped_column(ForeignKey('brands.id')); category_id:Mapped[Optional[int]]=mapped_column(ForeignKey('categories.id')); unit:Mapped[str]=mapped_column(String(30),default='عدد'); base_price:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); avg_cost:Mapped[Decimal]=mapped_column(Numeric(18,4),default=0,server_default='0'); min_stock:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); max_stock:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); barcode:Mapped[Optional[str]]=mapped_column(String(64),nullable=True,index=True); track_batch:Mapped[bool]=mapped_column(Boolean,default=False,server_default=sa_false()); active:Mapped[bool]=mapped_column(Boolean,default=True); specs:Mapped[dict]=mapped_column(JSON,default=dict)

class PriceRule(Base):
 __tablename__='price_rules'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); customer_group:Mapped[str]=mapped_column(String(100),default=''); price:Mapped[Optional[Decimal]]=mapped_column(Numeric(18,2)); discount_percent:Mapped[Decimal]=mapped_column(Numeric(8,2),default=0); starts_at:Mapped[Optional[datetime]]=mapped_column(); ends_at:Mapped[Optional[datetime]]=mapped_column(); active:Mapped[bool]=mapped_column(Boolean,default=True); min_qty:Mapped[Decimal]=mapped_column(Numeric(18,3),default=1,server_default='1')

class UnitConversion(Base):
 """واحد فرعی کالا (کارتن/پالت/...) با ضریب نسبت به «واحد پایه» (Product.unit)؛ تمام موجودی و قیمت‌ها به واحد پایه است."""
 __tablename__='unit_conversions'; __table_args__=(UniqueConstraint('product_id','unit'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id'),index=True); unit:Mapped[str]=mapped_column(String(30)); factor:Mapped[Decimal]=mapped_column(Numeric(18,4)); barcode:Mapped[Optional[str]]=mapped_column(String(64),nullable=True,index=True)

class Campaign(Base):
 """کمپین فروش زمان‌دار: درصد تخفیف روی یک کالا (یا همهٔ کالاها)، اختیاراً برای یک گروه مشتری و حداقل تعداد؛ در موتور قیمت با قانون‌های PriceRule رقابت می‌کند (ارزان‌تر برنده است)."""
 __tablename__='campaigns'; __table_args__=(Index('ix_campaign_active','company_id','active'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(150)); code:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); product_id:Mapped[Optional[int]]=mapped_column(ForeignKey('products.id'),nullable=True); customer_group:Mapped[str]=mapped_column(String(100),default='',server_default=''); discount_percent:Mapped[Decimal]=mapped_column(Numeric(8,2)); min_qty:Mapped[Decimal]=mapped_column(Numeric(18,3),default=1,server_default='1'); starts_at:Mapped[Optional[datetime]]=mapped_column(); ends_at:Mapped[Optional[datetime]]=mapped_column(); active:Mapped[bool]=mapped_column(Boolean,default=True)
