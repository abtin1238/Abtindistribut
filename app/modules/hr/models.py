from __future__ import annotations
from datetime import date, datetime, time
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Employee(Base):
 __tablename__='employees'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(200)); position:Mapped[str]=mapped_column(String(120),default=''); phone:Mapped[str]=mapped_column(String(50),default=''); salary:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); active:Mapped[bool]=mapped_column(Boolean,default=True)

class Attendance(Base):
 __tablename__='attendance'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); employee_id:Mapped[int]=mapped_column(ForeignKey('employees.id')); day:Mapped[date]=mapped_column(Date); check_in:Mapped[datetime]=mapped_column(DateTime); check_out:Mapped[Optional[datetime]]=mapped_column()

class LeaveRequest(Base):
 __tablename__='leave_requests'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); employee_id:Mapped[int]=mapped_column(ForeignKey('employees.id')); kind:Mapped[str]=mapped_column(String(20),default='annual'); start_date:Mapped[date]=mapped_column(Date); end_date:Mapped[date]=mapped_column(Date); reason:Mapped[str]=mapped_column(Text,default=''); status:Mapped[str]=mapped_column(String(20),default='pending'); decided_by:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); decided_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class PayrollRun(Base):
 __tablename__='payroll_runs'; __table_args__=(UniqueConstraint('company_id','period'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); period:Mapped[str]=mapped_column(String(7)); status:Mapped[str]=mapped_column(String(20),default='draft'); total_base:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); total_bonus:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); total_deduction:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); total_net:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); created_by:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id'),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class PayrollLine(Base):
 __tablename__='payroll_lines'; id:Mapped[int]=mapped_column(primary_key=True); run_id:Mapped[int]=mapped_column(ForeignKey('payroll_runs.id'),index=True); employee_id:Mapped[int]=mapped_column(ForeignKey('employees.id')); base:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); bonus:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); unpaid_days:Mapped[Decimal]=mapped_column(Numeric(6,1),default=0); deduction:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); net:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0)

class Shift(Base):
 __tablename__='shifts'; __table_args__=(UniqueConstraint('company_id','name'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); name:Mapped[str]=mapped_column(String(100)); start_time:Mapped[time]=mapped_column(Time); end_time:Mapped[time]=mapped_column(Time); grace_minutes:Mapped[int]=mapped_column(Integer,default=0,server_default='0'); active:Mapped[bool]=mapped_column(Boolean,default=True)

class EmployeeShift(Base):
 """شیفت جاری هر کارمند (یک ردیف به‌ازای کارمند)."""
 __tablename__='employee_shifts'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); employee_id:Mapped[int]=mapped_column(ForeignKey('employees.id'),unique=True); shift_id:Mapped[int]=mapped_column(ForeignKey('shifts.id'))
