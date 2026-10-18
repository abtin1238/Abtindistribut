from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Notification(Base):
 __tablename__='notifications'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); title:Mapped[str]=mapped_column(String(200)); body:Mapped[str]=mapped_column(Text); read:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
 event:Mapped[str]=mapped_column(String(40),default='',server_default=''); entity:Mapped[str]=mapped_column(String(30),default='',server_default=''); entity_id:Mapped[Optional[int]]=mapped_column(); dedupe_key:Mapped[Optional[str]]=mapped_column(String(100))

class NotificationPreference(Base):
 """ترجیح اعلان هر کاربر به‌ازای رویداد×کانال؛ نبودن ردیف = پیش‌فرض رویداد (ر.ک. app/services/notify.py)"""
 __tablename__='notification_preferences'; __table_args__=(UniqueConstraint('company_id','user_id','event','channel'),)
 id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); event:Mapped[str]=mapped_column(String(40)); channel:Mapped[str]=mapped_column(String(12)); enabled:Mapped[bool]=mapped_column(Boolean,default=True)

class NotificationDelivery(Base):
  """صف ارسال اعلان به کانال‌های بیرونی (email/sms/webpush)؛ ارسال با تلاش مجدد و ثبت خطا"""
  __tablename__='notification_deliveries'; __table_args__=(Index('ix_notif_deliv_status','status','id'),)
  id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); notification_id:Mapped[int]=mapped_column(ForeignKey('notifications.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); channel:Mapped[str]=mapped_column(String(12))
  status:Mapped[str]=mapped_column(String(10),default='pending'); attempts:Mapped[int]=mapped_column(Integer,default=0); error:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow); sent_at:Mapped[Optional[datetime]]=mapped_column(DateTime)

class PushSubscription(Base):
  __tablename__='push_subscriptions'; __table_args__=(UniqueConstraint('user_id','endpoint_hash'),)
  id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); endpoint:Mapped[str]=mapped_column(Text); endpoint_hash:Mapped[str]=mapped_column(String(64)); p256dh:Mapped[str]=mapped_column(String(200)); auth:Mapped[str]=mapped_column(String(100)); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
