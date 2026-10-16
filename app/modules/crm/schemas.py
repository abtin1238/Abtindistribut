from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class CustomerIn(BaseModel): code:str; name:str; phone:str=''; address:str=''; region:str=''; customer_group:str=''; credit_limit:Decimal=0; lat:Optional[float]=None; lng:Optional[float]=None

class AddressIn(BaseModel): title:str=Field(min_length=1,max_length=100); kind:str=Field('delivery',pattern='^(delivery|billing|other)$'); address:str=Field('',max_length=1000); region:str=Field('',max_length=120); lat:Optional[float]=Field(None,ge=-90,le=90); lng:Optional[float]=Field(None,ge=-180,le=180); is_default:bool=False

class AddressPatch(BaseModel): title:Optional[str]=Field(None,min_length=1,max_length=100); kind:Optional[str]=Field(None,pattern='^(delivery|billing|other)$'); address:Optional[str]=Field(None,max_length=1000); region:Optional[str]=Field(None,max_length=120); lat:Optional[float]=Field(None,ge=-90,le=90); lng:Optional[float]=Field(None,ge=-180,le=180); is_default:Optional[bool]=None

class ContactIn(BaseModel): name:str=Field(min_length=1,max_length=150); role:str=Field('',max_length=100); phone:str=Field('',max_length=50); email:str=Field('',max_length=200); is_primary:bool=False

class ContactPatch(BaseModel): name:Optional[str]=Field(None,min_length=1,max_length=150); role:Optional[str]=Field(None,max_length=100); phone:Optional[str]=Field(None,max_length=50); email:Optional[str]=Field(None,max_length=200); is_primary:Optional[bool]=None
