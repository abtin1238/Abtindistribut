from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class DeliveryIn(BaseModel): order_id:int; driver_id:int

class DeliveredItem(BaseModel): product_id:int; quantity:Decimal=Field(ge=0)

class DeliveryUpdate(BaseModel): status:str; reason:str=Field('',max_length=500); lat:Optional[float]=Field(None,ge=-90,le=90); lng:Optional[float]=Field(None,ge=-180,le=180); signature:str=Field('',max_length=400000); proof_photo:str=Field('',max_length=300); items:Optional[list[DeliveredItem]]=None

class CollectIn(BaseModel): amount:Decimal=Field(gt=0); method:str='cash'; reference:str=Field('',max_length=200); check_number:str=Field('',max_length=80); due_date:Optional[date]=None; bank:str=Field('',max_length=120)

class BulkAssignIn(BaseModel): order_ids:list[int]=Field(min_length=1,max_length=100); driver_id:int
