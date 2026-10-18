from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class ContractIn(BaseModel):
 title:str=Field(min_length=1,max_length=200);customer_id:Optional[int]=None;supplier_id:Optional[int]=None
 start_date:Optional[date]=None;end_date:Optional[date]=None;amount:Decimal=Field(default=Decimal(0),ge=0,max_digits=18,decimal_places=2);note:str=Field('',max_length=2000)

class ContractPatch(BaseModel):
 title:Optional[str]=Field(None,min_length=1,max_length=200);start_date:Optional[date]=None;end_date:Optional[date]=None;amount:Optional[Decimal]=Field(None,ge=0,max_digits=18,decimal_places=2);status:Optional[str]=None;note:Optional[str]=Field(None,max_length=2000)
