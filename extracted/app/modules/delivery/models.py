from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.database import Base

class Delivery(Base):
 __tablename__='deliveries'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); order_id:Mapped[int]=mapped_column(ForeignKey('orders.id')); driver_id:Mapped[int]=mapped_column(ForeignKey('users.id')); status:Mapped[str]=mapped_column(String(40),default='assigned'); reason:Mapped[str]=mapped_column(Text,default=''); lat:Mapped[Optional[float]]=mapped_column(); lng:Mapped[Optional[float]]=mapped_column(); proof_photo:Mapped[str]=mapped_column(String(300),default=''); signature:Mapped[str]=mapped_column(Text,default=''); delivered_at:Mapped[Optional[datetime]]=mapped_column(); gps_status:Mapped[str]=mapped_column(String(20),default='',server_default=''); distance_m:Mapped[Optional[float]]=mapped_column(); loaded_at:Mapped[Optional[datetime]]=mapped_column()
