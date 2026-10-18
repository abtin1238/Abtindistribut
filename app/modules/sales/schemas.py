from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from app.core.schema_utils import _rt

class ItemIn(BaseModel): product_id:int; quantity:Decimal; discount:Decimal=0; unit:str=Field('',max_length=30)  # واحد فرعی (کارتن/…)؛ خالی = واحد پایه

class OrderIn(BaseModel):
 customer_id:int; warehouse_id:int; items:list[ItemIn]; shipping:Decimal=Field(0,ge=0); note:str=Field('',max_length=40000)
 @field_validator('note')
 @classmethod
 def _n(cls,v): return _rt(v)

class InvoiceNoteIn(BaseModel):
 note:str=Field('',max_length=40000)
 @field_validator('note')
 @classmethod
 def _n(cls,v): return _rt(v)

class InvoiceTermsIn(BaseModel):
 terms:str=Field('',max_length=40000)
 @field_validator('terms')
 @classmethod
 def _t(cls,v): return _rt(v)

class ReturnItemIn(BaseModel): product_id:int; quantity:Decimal=Field(gt=0)

class ReturnIn(BaseModel): items:list[ReturnItemIn]=Field(min_length=1); reason:str=Field('',max_length=500)
