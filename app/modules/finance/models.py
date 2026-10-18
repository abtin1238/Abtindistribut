from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Payment(Base):
 __tablename__='payments'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id')); supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey('suppliers.id')); invoice_id:Mapped[Optional[int]]=mapped_column(ForeignKey('invoices.id')); amount:Mapped[Decimal]=mapped_column(Numeric(18,2)); kind:Mapped[str]=mapped_column(String(30)); method:Mapped[str]=mapped_column(String(30),default='cash'); reference:Mapped[str]=mapped_column(String(120),default=''); bank_account_id:Mapped[Optional[int]]=mapped_column(ForeignKey('bank_accounts.id'),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class Check(Base):
 __tablename__='checks'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); number:Mapped[str]=mapped_column(String(80)); kind:Mapped[str]=mapped_column(String(30)); amount:Mapped[Decimal]=mapped_column(Numeric(18,2)); due_date:Mapped[date]=mapped_column(Date); status:Mapped[str]=mapped_column(String(30),default='pending'); bank:Mapped[str]=mapped_column(String(120),default=''); party:Mapped[str]=mapped_column(String(200),default=''); notes:Mapped[str]=mapped_column(Text,default=''); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id'),nullable=True); supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey('suppliers.id'),nullable=True); endorsed_supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey('suppliers.id'),nullable=True); endorsed_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); bank_account_id:Mapped[Optional[int]]=mapped_column(ForeignKey('bank_accounts.id'),nullable=True,index=True); chequebook_id:Mapped[Optional[int]]=mapped_column(ForeignKey('chequebooks.id'),nullable=True,index=True)

class JournalEntry(Base):
 __tablename__='journal_entries'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); number:Mapped[str]=mapped_column(String(80),unique=True); description:Mapped[str]=mapped_column(Text); debit:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); credit:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); status:Mapped[str]=mapped_column(String(30),default='posted'); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); entry_date:Mapped[Optional[date]]=mapped_column(Date,default=lambda: utcnow().date(),index=True); source_type:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); source_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True); reverses_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True); created_by:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)

class Account(Base):
 __tablename__='accounts'; __table_args__=(UniqueConstraint('company_id','code'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); code:Mapped[str]=mapped_column(String(20)); name:Mapped[str]=mapped_column(String(200)); type:Mapped[str]=mapped_column(String(20)); active:Mapped[bool]=mapped_column(Boolean,default=True); parent_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True,index=True); level:Mapped[int]=mapped_column(Integer,default=3,server_default='3')

class JournalLine(Base):
 __tablename__='journal_lines'; id:Mapped[int]=mapped_column(primary_key=True); entry_id:Mapped[int]=mapped_column(ForeignKey('journal_entries.id'),index=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); account_id:Mapped[int]=mapped_column(ForeignKey('accounts.id'),index=True); debit:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); credit:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id'),index=True,nullable=True); supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey('suppliers.id'),index=True,nullable=True); memo:Mapped[str]=mapped_column(String(250),default='')

class FiscalPeriod(Base):
 __tablename__='fiscal_periods'; __table_args__=(Index('ix_fp_company_range','company_id','start_date','end_date'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(120)); start_date:Mapped[date]=mapped_column(Date); end_date:Mapped[date]=mapped_column(Date); closed:Mapped[bool]=mapped_column(Boolean,default=False); closed_by:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); closed_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class JournalTemplate(Base):
 """قالب سندسازی: سطرهای ثابت (حساب، سمت، ضریب از مبلغ پایه) که با یک مبلغ، سند متوازن می‌سازند"""
 __tablename__='journal_templates'; __table_args__=(UniqueConstraint('company_id','name'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); name:Mapped[str]=mapped_column(String(120)); description:Mapped[str]=mapped_column(String(300),default=''); lines:Mapped[list]=mapped_column(JSON); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
