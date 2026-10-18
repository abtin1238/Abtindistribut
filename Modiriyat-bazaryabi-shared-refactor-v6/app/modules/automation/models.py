from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Lead(Base):
 __tablename__='leads'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id')); owner_id:Mapped[int]=mapped_column(ForeignKey('users.id')); title:Mapped[str]=mapped_column(String(200)); stage:Mapped[str]=mapped_column(String(50),default='new'); next_followup:Mapped[Optional[date]]=mapped_column(); notes:Mapped[str]=mapped_column(Text,default=''); source:Mapped[str]=mapped_column(String(50),default='',server_default=''); value:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); lost_reason:Mapped[str]=mapped_column(String(200),default='',server_default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); closed_at:Mapped[Optional[datetime]]=mapped_column(); reminded_on:Mapped[Optional[date]]=mapped_column()

class LeadActivity(Base):
 __tablename__='lead_activities'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); lead_id:Mapped[int]=mapped_column(ForeignKey('leads.id'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); kind:Mapped[str]=mapped_column(String(20)); note:Mapped[str]=mapped_column(Text,default=''); from_stage:Mapped[str]=mapped_column(String(50),default=''); to_stage:Mapped[str]=mapped_column(String(50),default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class Task(Base):
 __tablename__='tasks'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); assignee_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); kind:Mapped[str]=mapped_column(String(20),default='task'); title:Mapped[str]=mapped_column(String(200)); due_date:Mapped[Optional[date]]=mapped_column(Date); status:Mapped[str]=mapped_column(String(20),default='open'); lead_id:Mapped[Optional[int]]=mapped_column(ForeignKey('leads.id')); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); done_at:Mapped[Optional[datetime]]=mapped_column(); reminded:Mapped[bool]=mapped_column(Boolean,default=False,server_default='0')

class Proposal(Base):
 __tablename__='proposals'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); number:Mapped[str]=mapped_column(String(80),unique=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id')); lead_id:Mapped[Optional[int]]=mapped_column(ForeignKey('leads.id')); owner_id:Mapped[int]=mapped_column(ForeignKey('users.id')); status:Mapped[str]=mapped_column(String(20),default='draft'); valid_until:Mapped[Optional[date]]=mapped_column(Date); total:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); order_id:Mapped[Optional[int]]=mapped_column(ForeignKey('orders.id')); notes:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class ProposalLine(Base):
 __tablename__='proposal_lines'; id:Mapped[int]=mapped_column(primary_key=True); proposal_id:Mapped[int]=mapped_column(ForeignKey('proposals.id'),index=True); product_id:Mapped[int]=mapped_column(ForeignKey('products.id')); quantity:Mapped[Decimal]=mapped_column(Numeric(18,3)); unit_price:Mapped[Decimal]=mapped_column(Numeric(18,2)); line_total:Mapped[Decimal]=mapped_column(Numeric(18,2))

class Target(Base):
 __tablename__='targets'; __table_args__=(UniqueConstraint('company_id','user_id','period'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); period:Mapped[str]=mapped_column(String(7)); sales_target:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0); commission_percent:Mapped[Decimal]=mapped_column(Numeric(8,2),default=0)
