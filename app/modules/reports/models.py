from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class ReportJob(Base):
 """کار پس‌زمینه‌ی ساخت خروجی گزارش (Excel/PDF)؛ فایل نتیجه زیر uploads/<company>/reports ذخیره و بعد از چند روز پاک می‌شود"""
 __tablename__='report_jobs'; __table_args__=(Index('ix_report_jobs_user','company_id','user_id','id'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 report:Mapped[str]=mapped_column(String(40)); params:Mapped[dict]=mapped_column(JSON,default=dict); fmt:Mapped[str]=mapped_column(String(8))
 status:Mapped[str]=mapped_column(String(12),default='queued'); error:Mapped[str]=mapped_column(Text,default=''); title:Mapped[str]=mapped_column(String(200),default='')
 filename:Mapped[str]=mapped_column(String(200),default=''); path:Mapped[str]=mapped_column(String(500),default='')
 created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); finished_at:Mapped[Optional[datetime]]=mapped_column(DateTime)
