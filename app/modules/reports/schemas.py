from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Literal

# ---------------------------------------------------------------- صف پس‌زمینه
class JobIn(BaseModel):
 report:str;format:Literal['xlsx','pdf']='xlsx';params:dict[str,Any]={}
