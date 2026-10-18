from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Sequence(Base):
 __tablename__='sequences'; key:Mapped[str]=mapped_column(String(120),primary_key=True); value:Mapped[int]=mapped_column(Integer,default=0)

class IdempotencyRecord(Base):
 __tablename__='idempotency_records'; __table_args__=(UniqueConstraint('scope','key',name='ux_idem_scope_key'),); id:Mapped[int]=mapped_column(primary_key=True); scope:Mapped[str]=mapped_column(String(64)); key:Mapped[str]=mapped_column(String(120)); fingerprint:Mapped[str]=mapped_column(String(64)); status:Mapped[str]=mapped_column(String(12),default='processing',server_default='processing'); response_status:Mapped[Optional[int]]=mapped_column(); response_body:Mapped[Optional[str]]=mapped_column(Text); response_type:Mapped[str]=mapped_column(String(100),default='',server_default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow,index=True)
