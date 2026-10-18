from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class ProductIn(BaseModel): sku:str; name:str; unit:str='عدد'; base_price:Decimal=0; min_stock:Decimal=0; max_stock:Decimal=Field(0,ge=0); track_batch:bool=False; barcode:Optional[str]=Field(None,max_length=64); brand_id:Optional[int]=None; category_id:Optional[int]=None

class ProductPatch(BaseModel): name:Optional[str]=None; unit:Optional[str]=None; base_price:Optional[Decimal]=None; min_stock:Optional[Decimal]=None; max_stock:Optional[Decimal]=Field(None,ge=0); track_batch:Optional[bool]=None; barcode:Optional[str]=Field(None,max_length=64); brand_id:Optional[int]=None; category_id:Optional[int]=None; active:Optional[bool]=None

class BrandIn(BaseModel): name:str

class CategoryIn(BaseModel): name:str; parent_id:Optional[int]=None

class PriceRuleIn(BaseModel): product_id:int; customer_group:str=''; price:Optional[Decimal]=None; discount_percent:Decimal=0; starts_at:Optional[datetime]=None; ends_at:Optional[datetime]=None; min_qty:Decimal=Field(1,gt=0)

class UnitIn(BaseModel): unit:str=Field(min_length=1,max_length=30); factor:Decimal=Field(gt=0); barcode:Optional[str]=Field(None,max_length=64)

class CampaignIn(BaseModel): name:str=Field(min_length=1,max_length=150); code:Optional[str]=Field(None,max_length=40); product_id:Optional[int]=None; customer_group:str=Field('',max_length=100); discount_percent:Decimal=Field(gt=0,le=100); min_qty:Decimal=Field(1,gt=0); starts_at:Optional[datetime]=None; ends_at:Optional[datetime]=None
