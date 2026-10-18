from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class VisitPlan(Base):
 __tablename__='visit_plans'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); day:Mapped[date]=mapped_column(Date); status:Mapped[str]=mapped_column(String(30),default='planned')

class VisitPlanItem(Base):
 __tablename__='visit_plan_items'; id:Mapped[int]=mapped_column(primary_key=True); plan_id:Mapped[int]=mapped_column(ForeignKey('visit_plans.id')); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id')); sequence:Mapped[int]=mapped_column(Integer,default=1); status:Mapped[str]=mapped_column(String(30),default='pending')

class Visit(Base):
 __tablename__='visits'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); plan_id:Mapped[Optional[int]]=mapped_column(ForeignKey('visit_plans.id')); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); started_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); ended_at:Mapped[Optional[datetime]]=mapped_column(); lat:Mapped[Optional[float]]=mapped_column(); lng:Mapped[Optional[float]]=mapped_column(); note:Mapped[str]=mapped_column(Text,default=''); photo:Mapped[str]=mapped_column(String(300),default=''); result:Mapped[str]=mapped_column(String(30),default='',server_default=''); no_order_reason:Mapped[str]=mapped_column(String(200),default='',server_default=''); distance_m:Mapped[Optional[float]]=mapped_column(); gps_status:Mapped[str]=mapped_column(String(20),default='',server_default=''); order_id:Mapped[Optional[int]]=mapped_column(ForeignKey('orders.id'))
