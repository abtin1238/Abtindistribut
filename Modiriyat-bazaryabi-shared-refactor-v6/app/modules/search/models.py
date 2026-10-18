from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import utcnow
from app.core.database import Base

class SavedFilter(Base):
  __tablename__='saved_filters'; __table_args__=(UniqueConstraint('company_id','user_id','entity','name'),)
  id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); entity:Mapped[str]=mapped_column(String(30)); name:Mapped[str]=mapped_column(String(100)); query:Mapped[dict]=mapped_column(JSON,default=dict); shared:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
