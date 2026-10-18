from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from typing import Optional

class WarehouseIn(BaseModel): company_id:int; branch_id:Optional[int]=None; name:str; address:str=''

class StockIn(BaseModel): warehouse_id:int; product_id:int; quantity:Decimal; kind:str='in'; reference:str='manual'; reason:str=Field('',max_length=200); batch_no:str=Field('',max_length=60); expiry_date:Optional[date]=None

class TransferItemIn(BaseModel): product_id:int; quantity:Decimal=Field(gt=0); unit:str=Field('',max_length=30)

class TransferIn(BaseModel):
 """انتقال چندقلمی: items؛ فرم قدیمی تک‌قلمی (product_id+quantity) هم پذیرفته می‌شود. کالای تکراری جمع می‌شود."""
 from_warehouse_id:int; to_warehouse_id:int; items:list[TransferItemIn]=Field(default_factory=list); product_id:Optional[int]=None; quantity:Optional[Decimal]=Field(None,gt=0); unit:str=Field('',max_length=30); note:str=''
 @model_validator(mode='after')
 def _norm(self):
  rows=list(self.items)
  if not rows:
   if self.product_id is None or self.quantity is None: raise ValueError('حداقل یک قلم برای انتقال لازم است')
   rows=[TransferItemIn(product_id=self.product_id,quantity=self.quantity,unit=self.unit)]
  merged={}
  for r in rows: merged[(r.product_id,r.unit.strip())]=merged.get((r.product_id,r.unit.strip()),Decimal(0))+r.quantity
  self.items=[TransferItemIn(product_id=k[0],quantity=v,unit=k[1]) for k,v in merged.items()]
  return self

class LocationIn(BaseModel): location:str=Field(max_length=60)

class CountIn(BaseModel): warehouse_id:int; product_ids:Optional[list[int]]=None; note:str=Field('',max_length=500)

class CountLineIn(BaseModel): product_id:int; counted_qty:Decimal=Field(ge=0)

class CountLinesIn(BaseModel): lines:list[CountLineIn]=Field(min_length=1)

class CountApproveIn(BaseModel): reason:str=Field('',max_length=200)
