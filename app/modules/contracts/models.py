from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.config import utcnow
from app.core.database import Base

class Contract(Base):
 __tablename__='contracts'; __table_args__=(UniqueConstraint('company_id','number',name='ux_contract_number'),); id:Mapped[int]=mapped_column(primary_key=True); company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True); number:Mapped[str]=mapped_column(String(80)); title:Mapped[str]=mapped_column(String(200)); customer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id')); supplier_id:Mapped[Optional[int]]=mapped_column(ForeignKey('suppliers.id')); start_date:Mapped[Optional[date]]=mapped_column(Date); end_date:Mapped[Optional[date]]=mapped_column(Date); amount:Mapped[Decimal]=mapped_column(Numeric(18,2),default=0,server_default='0'); status:Mapped[str]=mapped_column(String(20),default='draft',server_default='draft'); note:Mapped[str]=mapped_column(Text,default='',server_default=''); created_by:Mapped[Optional[int]]=mapped_column(); created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
