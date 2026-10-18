from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class ApiKeyIn(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 role_id:int
 expires_in_days:Optional[int]=Field(None,ge=1,le=3650)

class WebhookIn(BaseModel):
 url:str=Field(min_length=8,max_length=500)
 events:list[str]=Field(default_factory=lambda:['*'],min_length=1,max_length=40)

class WebhookPatch(BaseModel):
 url:Optional[str]=Field(None,min_length=8,max_length=500)
 events:Optional[list[str]]=Field(None,min_length=1,max_length=40)
 active:Optional[bool]=None
