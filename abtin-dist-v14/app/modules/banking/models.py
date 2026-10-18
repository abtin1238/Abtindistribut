from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class BankAccount(Base):
 """حساب بانکی شرکت؛ هر حساب یک حساب معین اختصاصی در دفتر کل دارد (`ledger_code`، زیرمجموعه‌ی 1120) و مانده‌اش همیشه از اسناد محاسبه می‌شود، نه ذخیره."""
 __tablename__='bank_accounts'; __table_args__=(UniqueConstraint('company_id','name'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); name:Mapped[str]=mapped_column(String(150)); bank_name:Mapped[str]=mapped_column(String(120),default='',server_default=''); branch:Mapped[str]=mapped_column(String(120),default='',server_default=''); account_number:Mapped[str]=mapped_column(String(60),default='',server_default=''); iban:Mapped[str]=mapped_column(String(40),default='',server_default=''); holder:Mapped[str]=mapped_column(String(200),default='',server_default='')
 opening_balance:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); ledger_code:Mapped[str]=mapped_column(String(20),default='',server_default=''); active:Mapped[bool]=mapped_column(Boolean,default=True,server_default='1'); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class Chequebook(Base):
 """دسته‌چک صادره: برگ‌ها start_no..end_no؛ استفاده‌شده = چکی (حتی باطل) با همین شماره در همین دسته"""
 __tablename__='chequebooks'
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); bank_account_id:Mapped[int]=mapped_column(ForeignKey('bank_accounts.id'),index=True); series:Mapped[str]=mapped_column(String(40),default='',server_default=''); start_no:Mapped[int]=mapped_column(Integer); end_no:Mapped[int]=mapped_column(Integer)
 status:Mapped[str]=mapped_column(String(20),default='active',server_default='active'); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class CheckHistory(Base):
 """تاریخچه‌ی چک: ثبت، تغییر وضعیت، خرج، تعیین حساب، ابطال برگ"""
 __tablename__='check_history'
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); check_id:Mapped[int]=mapped_column(ForeignKey('checks.id'),index=True); user_id:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); action:Mapped[str]=mapped_column(String(30)); from_status:Mapped[str]=mapped_column(String(30),default='',server_default=''); to_status:Mapped[str]=mapped_column(String(30),default='',server_default=''); note:Mapped[str]=mapped_column(String(300),default='',server_default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class BankReconciliation(Base):
 """مغایرت‌گیری با صورت‌حساب بانک: سطرهای دفتر که با صورت‌حساب تطبیق داده شدند + مانده‌ی صورت‌حساب"""
 __tablename__='bank_reconciliations'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); bank_account_id:Mapped[int]=mapped_column(ForeignKey('bank_accounts.id'),index=True); statement_balance:Mapped[Decimal]=mapped_column(Numeric(18,2)); cleared_balance:Mapped[Decimal]=mapped_column(Numeric(18,2)); book_balance:Mapped[Decimal]=mapped_column(Numeric(18,2)); difference:Mapped[Decimal]=mapped_column(Numeric(18,2)); note:Mapped[str]=mapped_column(String(300),default=''); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class BankReconciliationLine(Base):
 __tablename__='bank_reconciliation_lines'; id:Mapped[int]=mapped_column(primary_key=True); reconciliation_id:Mapped[int]=mapped_column(ForeignKey('bank_reconciliations.id'),index=True); journal_line_id:Mapped[int]=mapped_column(ForeignKey('journal_lines.id'),unique=True)
