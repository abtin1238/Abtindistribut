from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class SyncEvent(Base):
 __tablename__='sync_events'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); client_event_id:Mapped[str]=mapped_column(String(120)); event_type:Mapped[str]=mapped_column(String(80)); payload:Mapped[dict]=mapped_column(JSON,default=dict); status:Mapped[str]=mapped_column(String(20),default='applied',server_default='applied'); error:Mapped[str]=mapped_column(Text,default='',server_default=''); result_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
