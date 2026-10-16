from __future__ import annotations
from pydantic import BaseModel, Field

class PrefsIn(BaseModel): prefs:dict[str,dict[str,bool]]

class ContactIn(BaseModel): email:str=Field('',max_length=200);phone:str=Field('',max_length=30)

class TestIn(BaseModel): channel:str

class PushKeys(BaseModel): p256dh:str=Field(max_length=200);auth:str=Field(max_length=100)

class PushIn(BaseModel): endpoint:str=Field(max_length=2000);keys:PushKeys

class PushDel(BaseModel): endpoint:str=Field(max_length=2000)
