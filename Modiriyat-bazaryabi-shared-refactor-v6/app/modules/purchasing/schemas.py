from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class PurchaseItemIn(BaseModel): product_id:int; quantity:Decimal=Field(gt=0); unit_cost:Decimal=Field(ge=0); discount:Decimal=Field(0,ge=0); batch_no:str=Field('',max_length=60); expiry_date:Optional[date]=None; unit:str=Field('',max_length=30)

class PurchaseIn(BaseModel): supplier_id:int; warehouse_id:int; items:list[PurchaseItemIn]; freight:Decimal=Field(0,ge=0)

class PurchaseReturnItem(BaseModel): product_id:int; quantity:Decimal=Field(gt=0)

class PurchaseReturnIn(BaseModel): items:list[PurchaseReturnItem]=Field(min_length=1); reason:str=''

class PurchaseReceiptItem(BaseModel): product_id:int; quantity:Decimal=Field(gt=0)

class PurchaseReceiptIn(BaseModel): items:Optional[list[PurchaseReceiptItem]]=None   # خالی = دریافت همهٔ باقیمانده

class CostAllocationIn(BaseModel): label:str=Field(min_length=1,max_length=100); amount:Decimal=Field(gt=0); basis:str=Field('value',pattern='^(value|qty)$')
