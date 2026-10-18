from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Literal, Optional

class FiscalPeriodIn(BaseModel): name:str; start_date:date; end_date:date

class PaymentIn(BaseModel): customer_id:Optional[int]=None; supplier_id:Optional[int]=None; invoice_id:Optional[int]=None; amount:Decimal=Field(gt=0); kind:str='receipt'; method:str='cash'; reference:str=''; bank_account_id:Optional[int]=None

class CheckIn(BaseModel): number:str=Field('',max_length=80); kind:str='received'; amount:Decimal=Field(gt=0); due_date:date; bank:str=''; party:str=''; notes:str=''; customer_id:Optional[int]=None; supplier_id:Optional[int]=None; bank_account_id:Optional[int]=None; chequebook_id:Optional[int]=None

class CheckStatusIn(BaseModel): status:str; bank_account_id:Optional[int]=None; note:str=Field('',max_length=300); fee:Decimal=Field(0,ge=0)

class CheckEndorseIn(BaseModel): supplier_id:int

class JLineIn(BaseModel): account_code:str=Field(min_length=1,max_length=20); debit:Decimal=Field(0,ge=0); credit:Decimal=Field(0,ge=0); customer_id:Optional[int]=None; supplier_id:Optional[int]=None; memo:str=Field('',max_length=250)

class JournalIn(BaseModel): description:str=Field(min_length=1); lines:list[JLineIn]=Field(min_length=2); entry_date:Optional[date]=None

class AccountIn(BaseModel): code:str=Field(pattern=r'^\d{3,10}$'); name:str=Field(min_length=1,max_length=200); type:str; parent_code:Optional[str]=Field(None,pattern=r'^\d{1,10}$')

class AccountPatch(BaseModel): name:Optional[str]=Field(None,min_length=1,max_length=200); active:Optional[bool]=None

class TemplateLineIn(BaseModel): account_code:str=Field(pattern=r'^\d{3,10}$'); side:Literal['debit','credit']; ratio:Decimal=Field(1,gt=0); memo:str=Field('',max_length=200)

class JournalTemplateIn(BaseModel): name:str=Field(min_length=1,max_length=120); description:str=Field('',max_length=300); lines:list[TemplateLineIn]=Field(min_length=2)

class TemplatePostIn(BaseModel): amount:Decimal=Field(gt=0); description:str=Field('',max_length=300); entry_date:Optional[date]=None
