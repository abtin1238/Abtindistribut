from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.core.schema_utils import _rt

class LeadIn(BaseModel):
 customer_id:Optional[int]=None; title:str=Field(min_length=1,max_length=200); stage:str='new'; next_followup:Optional[date]=None; notes:str=Field('',max_length=40000); source:str=Field('',max_length=50); value:Decimal=Field(0,ge=0)
 @field_validator('notes')
 @classmethod
 def _rt_notes(cls,v): return _rt(v)

class LeadStageIn(BaseModel): stage:str; lost_reason:str=Field('',max_length=200); note:str=Field('',max_length=1000)

class LeadActivityIn(BaseModel):
 kind:str='note'; note:str=Field('',max_length=40000); next_followup:Optional[date]=None
 @field_validator('note')
 @classmethod
 def _rt_note(cls,v): return _rt(v)

class TaskIn(BaseModel): title:str=Field(min_length=1,max_length=200); kind:str='task'; due_date:Optional[date]=None; assignee_id:Optional[int]=None; lead_id:Optional[int]=None; customer_id:Optional[int]=None

class TaskPatch(BaseModel): status:str

class ProposalItemIn(BaseModel): product_id:int; quantity:Decimal=Field(gt=0)

class ProposalIn(BaseModel):
 customer_id:int; lead_id:Optional[int]=None; valid_until:Optional[date]=None; notes:str=Field('',max_length=40000); items:list[ProposalItemIn]=Field(min_length=1)
 @field_validator('notes')
 @classmethod
 def _rt_notes(cls,v): return _rt(v)

class ProposalAcceptIn(BaseModel): warehouse_id:int

class TargetIn(BaseModel): user_id:int; period:str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$'); sales_target:Decimal=Field(ge=0); commission_percent:Decimal=Field(0,ge=0,le=100)
