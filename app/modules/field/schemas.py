from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.core.schema_utils import _rt

class VisitIn(BaseModel):
 customer_id:int; plan_id:Optional[int]=None; lat:Optional[float]=Field(None,ge=-90,le=90); lng:Optional[float]=Field(None,ge=-180,le=180); note:str=Field('',max_length=40000)
 @field_validator('note')
 @classmethod
 def _rt_note(cls,v): return _rt(v)

class PlanIn(BaseModel): user_id:int; day:date; customer_ids:list[int]=[]

class VisitFinishIn(BaseModel):
 result:str=''; no_order_reason:str=Field('',max_length=200); note:Optional[str]=Field(None,max_length=40000); order_id:Optional[int]=None
 @field_validator('note')
 @classmethod
 def _rt_note(cls,v): return _rt(v)

class VisitRadiusIn(BaseModel): radius_m:int=Field(ge=10,le=5000)
