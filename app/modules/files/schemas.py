from __future__ import annotations
from pydantic import BaseModel

class DocPatch(BaseModel): restricted:bool
