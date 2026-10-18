from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class GpsPoint(Base):
 __tablename__='gps_points'; __table_args__=(UniqueConstraint('company_id','user_id','client_id'),Index('ix_gps_user_time','company_id','user_id','recorded_at'))
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); client_id:Mapped[Optional[str]]=mapped_column(String(64))
 lat:Mapped[float]=mapped_column(); lng:Mapped[float]=mapped_column(); accuracy_m:Mapped[Optional[float]]=mapped_column(); speed_mps:Mapped[Optional[float]]=mapped_column()
 recorded_at:Mapped[datetime]=mapped_column(DateTime); received_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)


class Geofence(Base):
 """ناحیهٔ دایره‌ای (انبار/منطقهٔ مشتری/ناحیهٔ ممنوع)؛ حذف = غیرفعال‌سازی."""
 __tablename__='geofences'; __table_args__=(UniqueConstraint('company_id','name'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); name:Mapped[str]=mapped_column(String(100)); kind:Mapped[str]=mapped_column(String(20),default='area',server_default='area'); lat:Mapped[float]=mapped_column(Float); lng:Mapped[float]=mapped_column(Float); radius_m:Mapped[float]=mapped_column(Float); active:Mapped[bool]=mapped_column(Boolean,default=True); created_by:Mapped[int]=mapped_column(ForeignKey('users.id')); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class GeofenceEvent(Base):
 """رویداد تغییرناپذیر ورود/خروج کاربر از ناحیه (محاسبه‌شده هنگام ثبت نقاط GPS)."""
 __tablename__='geofence_events'; __table_args__=(Index('ix_gfe_user_time','company_id','user_id','at'),UniqueConstraint('company_id','user_id','geofence_id','kind','at')); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); geofence_id:Mapped[int]=mapped_column(ForeignKey('geofences.id'),index=True); kind:Mapped[str]=mapped_column(String(10)); at:Mapped[datetime]=mapped_column(DateTime); lat:Mapped[float]=mapped_column(Float); lng:Mapped[float]=mapped_column(Float)
