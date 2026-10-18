from __future__ import annotations
from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class BankAccountIn(BaseModel): name:str=Field(min_length=1,max_length=150); bank_name:str=Field('',max_length=120); branch:str=Field('',max_length=120); account_number:str=Field('',max_length=60); iban:str=Field('',max_length=40); holder:str=Field('',max_length=200); opening_balance:Decimal=Field(0,ge=0)

class BankAccountPatch(BaseModel): name:Optional[str]=Field(None,min_length=1,max_length=150); bank_name:Optional[str]=Field(None,max_length=120); branch:Optional[str]=Field(None,max_length=120); account_number:Optional[str]=Field(None,max_length=60); iban:Optional[str]=Field(None,max_length=40); holder:Optional[str]=Field(None,max_length=200); active:Optional[bool]=None

class ChequebookIn(BaseModel): bank_account_id:int; series:str=Field('',max_length=40); start_no:int=Field(ge=1); end_no:int=Field(ge=1)

class ChequebookPatch(BaseModel): status:str

class LeafVoidIn(BaseModel): number:str=Field(min_length=1,max_length=80); note:str=Field('',max_length=300)

class BankTransferIn(BaseModel): from_account_id:Optional[int]=None; to_account_id:Optional[int]=None; amount:Decimal=Field(gt=0); note:str=Field('',max_length=200)

class BankChargeIn(BaseModel): kind:Literal['fee','interest']; amount:Decimal=Field(gt=0); note:str=Field('',max_length=200)

class ReconcileIn(BaseModel): statement_balance:Decimal; line_ids:list[int]=Field(min_length=1); note:str=Field('',max_length=300)
