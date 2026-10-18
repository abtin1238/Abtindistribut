from __future__ import annotations
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Setting(Base):
 __tablename__='settings'; id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id')); key:Mapped[str]=mapped_column(String(80)); value:Mapped[str]=mapped_column(Text,default='')
