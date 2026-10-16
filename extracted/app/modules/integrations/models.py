from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class ApiKey(Base):
 __tablename__='api_keys'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); name:Mapped[str]=mapped_column(String(100)); prefix:Mapped[str]=mapped_column(String(16),unique=True); key_hash:Mapped[str]=mapped_column(String(64)); role_id:Mapped[int]=mapped_column(ForeignKey('roles.id')); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); expires_at:Mapped[Optional[datetime]]=mapped_column(DateTime); last_used_at:Mapped[Optional[datetime]]=mapped_column(DateTime); revoked_at:Mapped[Optional[datetime]]=mapped_column(DateTime); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class WebhookEndpoint(Base):
 __tablename__='webhook_endpoints'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); url:Mapped[str]=mapped_column(String(500)); secret:Mapped[str]=mapped_column(String(80)); events:Mapped[list]=mapped_column(JSON,default=list); active:Mapped[bool]=mapped_column(Boolean,default=True,server_default='1'); consecutive_failures:Mapped[int]=mapped_column(Integer,default=0,server_default='0'); created_by:Mapped[Optional[int]]=mapped_column(); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class WebhookDelivery(Base):
 __tablename__='webhook_deliveries'; __table_args__=(Index('ix_whd_due','status','next_try_at'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); endpoint_id:Mapped[int]=mapped_column(ForeignKey('webhook_endpoints.id'),index=True); event:Mapped[str]=mapped_column(String(60)); event_id:Mapped[str]=mapped_column(String(40)); payload:Mapped[dict]=mapped_column(JSON,default=dict); status:Mapped[str]=mapped_column(String(15),default='pending',server_default='pending'); attempts:Mapped[int]=mapped_column(Integer,default=0,server_default='0'); next_try_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); response_code:Mapped[Optional[int]]=mapped_column(); error:Mapped[str]=mapped_column(String(300),default='',server_default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
