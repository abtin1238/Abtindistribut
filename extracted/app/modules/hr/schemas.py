from __future__ import annotations
from datetime import date, time
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class LeaveIn(BaseModel): employee_id:int; kind:str='annual'; start_date:date; end_date:date; reason:str=''

class PayrollRunIn(BaseModel): period:str; bonuses:dict[int,Decimal]={}

class EmployeeIn(BaseModel): name:str; position:str=''; phone:str=''; salary:Decimal=0

class ShiftIn(BaseModel): name:str=Field(min_length=1,max_length=100); start_time:time; end_time:time; grace_minutes:int=Field(0,ge=0,le=180)

class ShiftPatch(BaseModel): name:Optional[str]=Field(None,min_length=1,max_length=100); start_time:Optional[time]=None; end_time:Optional[time]=None; grace_minutes:Optional[int]=Field(None,ge=0,le=180); active:Optional[bool]=None

class EmployeeShiftIn(BaseModel): shift_id:Optional[int]=None
