from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import event, Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Group(Base):
 __tablename__='groups'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(200),unique=True); active:Mapped[bool]=mapped_column(Boolean,default=True)

class Company(Base):
 __tablename__='companies'; id:Mapped[int]=mapped_column(primary_key=True); group_id:Mapped[int]=mapped_column(ForeignKey('groups.id')); parent_company_id:Mapped[Optional[int]]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(200)); code:Mapped[str]=mapped_column(String(50),unique=True); active:Mapped[bool]=mapped_column(Boolean,default=True)

class Branch(Base):
 __tablename__='branches'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(200)); address:Mapped[str]=mapped_column(Text,default=''); lat:Mapped[Optional[float]]=mapped_column(); lng:Mapped[Optional[float]]=mapped_column(); active:Mapped[bool]=mapped_column(Boolean,default=True)

class Role(Base):
 __tablename__='roles'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[Optional[int]]=mapped_column(ForeignKey('companies.id')); name:Mapped[str]=mapped_column(String(100)); permissions:Mapped[list]=mapped_column(JSON,default=list); max_discount_percent:Mapped[Optional[Decimal]]=mapped_column(Numeric(5,2),nullable=True)  # سقف تخفیف دستی (٪ مبلغ قلم)؛ None = بدون سقف

class User(Base):
 __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(100),unique=True); password_hash:Mapped[str]=mapped_column(String(300)); name:Mapped[str]=mapped_column(String(200)); role_id:Mapped[int]=mapped_column(ForeignKey('roles.id')); active:Mapped[bool]=mapped_column(Boolean,default=True); failed_attempts:Mapped[int]=mapped_column(Integer,default=0,server_default='0'); locked_until:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); email:Mapped[str]=mapped_column(String(200),default='',server_default=''); phone:Mapped[str]=mapped_column(String(30),default='',server_default='')

class Membership(Base):
 __tablename__='memberships'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); branch_id:Mapped[Optional[int]]=mapped_column(ForeignKey('branches.id')); is_default:Mapped[bool]=mapped_column(Boolean,default=False)

class SessionToken(Base):
 __tablename__='sessions'; token:Mapped[str]=mapped_column(String(120),primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); expires_at:Mapped[datetime]=mapped_column(DateTime); created_at:Mapped[Optional[datetime]]=mapped_column(DateTime,default=None); ip:Mapped[Optional[str]]=mapped_column(String(64),default=None); user_agent:Mapped[Optional[str]]=mapped_column(String(300),default=None)

class RefreshToken(Base):
 """refresh token چرخشی؛ فقط هش SHA-256 ذخیره می‌شود. `family` همه‌ی نسل‌های یک ورود را به هم وصل می‌کند (تشخیص استفاده‌ی مجدد)."""
 __tablename__='refresh_tokens'; id:Mapped[int]=mapped_column(primary_key=True); token_hash:Mapped[str]=mapped_column(String(64),unique=True,index=True); family:Mapped[str]=mapped_column(String(40),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); session_token:Mapped[Optional[str]]=mapped_column(String(120),default=None); expires_at:Mapped[datetime]=mapped_column(DateTime); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); revoked_at:Mapped[Optional[datetime]]=mapped_column(DateTime,default=None); ip:Mapped[Optional[str]]=mapped_column(String(64),default=None); user_agent:Mapped[Optional[str]]=mapped_column(String(300),default=None)

class Audit(Base):
 __tablename__='audit_logs'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[Optional[int]]=mapped_column(ForeignKey('users.id')); action:Mapped[str]=mapped_column(String(80)); entity:Mapped[str]=mapped_column(String(80)); entity_id:Mapped[Optional[int]]=mapped_column(); detail:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); ip:Mapped[Optional[str]]=mapped_column(String(64),default=None); request_id:Mapped[Optional[str]]=mapped_column(String(64),default=None)

@event.listens_for(Audit,'before_update')
@event.listens_for(Audit,'before_delete')
def _audit_immutable(mapper,conn,target):
 raise RuntimeError('Audit Log تغییرناپذیر است')
