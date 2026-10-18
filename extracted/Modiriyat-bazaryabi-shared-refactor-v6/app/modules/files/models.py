from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Document(Base):
 __tablename__='documents'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); entity:Mapped[str]=mapped_column(String(80)); entity_id:Mapped[int]=mapped_column(); filename:Mapped[str]=mapped_column(String(250)); path:Mapped[str]=mapped_column(String(500)); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
 owner_id:Mapped[Optional[int]]=mapped_column(); size:Mapped[int]=mapped_column(Integer,default=0,server_default='0'); mime:Mapped[str]=mapped_column(String(100),default='',server_default=''); sha256:Mapped[str]=mapped_column(String(64),default='',server_default=''); restricted:Mapped[bool]=mapped_column(Boolean,default=False,server_default='0'); current_version:Mapped[int]=mapped_column(Integer,default=1,server_default='1'); deleted_at:Mapped[Optional[datetime]]=mapped_column(DateTime)

class FileVersion(Base):
  """نسخه‌های هر فایل پیوست؛ نسخه‌ی قبلی هرگز حذف/بازنویسی نمی‌شود"""
  __tablename__='file_versions'; __table_args__=(UniqueConstraint('document_id','version'),)
  id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); document_id:Mapped[int]=mapped_column(ForeignKey('documents.id'),index=True); version:Mapped[int]=mapped_column(Integer); filename:Mapped[str]=mapped_column(String(250)); path:Mapped[str]=mapped_column(String(500)); size:Mapped[int]=mapped_column(Integer,default=0); mime:Mapped[str]=mapped_column(String(100),default=''); sha256:Mapped[str]=mapped_column(String(64),default=''); note:Mapped[str]=mapped_column(String(300),default=''); uploaded_by:Mapped[Optional[int]]=mapped_column(); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
