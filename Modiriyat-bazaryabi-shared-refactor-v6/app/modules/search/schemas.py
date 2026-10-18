from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Any

class AdvIn(BaseModel):
 entity:str;q:str=Field('',max_length=200);filters:list[dict[str,Any]]=[];sort:Optional[str]=None;order:Optional[str]=None;page:int=Field(1,ge=1,le=100000);page_size:int=Field(25,ge=1,le=100)

class SavedIn(BaseModel):
 entity:str;name:str=Field(min_length=1,max_length=100);query:dict[str,Any]=Field(default_factory=dict);shared:bool=False
