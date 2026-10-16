from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional

class LoginIn(BaseModel): username:str; password:str; company_id:Optional[int]=None

class PasswordChangeIn(BaseModel): old_password:str; new_password:str

class OrgIn(BaseModel): name:str; code:str; parent_company_id:Optional[int]=None

class BranchIn(BaseModel): company_id:int; name:str; address:str=''; lat:Optional[float]=None; lng:Optional[float]=None

class UserIn(BaseModel): username:str; password:str; name:str; role_id:int; company_ids:list[int]=[]; branch_id:Optional[int]=None

class RoleIn(BaseModel): name:str; permissions:list[str]=[]; company_id:Optional[int]=None; max_discount_percent:Optional[Decimal]=Field(None,ge=0,le=100)

class MembershipIn(BaseModel): user_id:int; company_id:int; branch_id:Optional[int]=None; is_default:bool=False

class PasswordResetIn(BaseModel): new_password:str

class UserPatch(BaseModel): role_id:Optional[int]=None; active:Optional[bool]=None
