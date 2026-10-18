from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class GpsPointIn(BaseModel): lat:float=Field(ge=-90,le=90); lng:float=Field(ge=-180,le=180); accuracy_m:Optional[float]=Field(None,ge=0,le=100000); speed_mps:Optional[float]=Field(None,ge=0,le=500); recorded_at:Optional[datetime]=None; client_id:Optional[str]=Field(None,max_length=64)

class GpsBatchIn(BaseModel): points:list[GpsPointIn]=Field(min_length=1,max_length=500)

class TrackingSettingsIn(BaseModel): enabled:bool=True; work_start:str=Field('08:00',pattern=r'^([01]\d|2[0-3]):[0-5]\d$'); work_end:str=Field('19:00',pattern=r'^([01]\d|2[0-3]):[0-5]\d$'); work_days:list[int]=Field([5,6,0,1,2,3],max_length=7); interval_s:int=Field(60,ge=15,le=3600); min_distance_m:int=Field(25,ge=0,le=2000); retention_days:int=Field(90,ge=7,le=730); tz_offset_min:int=Field(210,ge=-720,le=840)

class GeofenceIn(BaseModel): name:str=Field(min_length=1,max_length=100); kind:str=Field('area',pattern='^(area|depot|customer|restricted)$'); lat:float=Field(ge=-90,le=90); lng:float=Field(ge=-180,le=180); radius_m:float=Field(gt=0,le=50000)

class GeofencePatch(BaseModel): name:Optional[str]=Field(None,min_length=1,max_length=100); kind:Optional[str]=Field(None,pattern='^(area|depot|customer|restricted)$'); lat:Optional[float]=Field(None,ge=-90,le=90); lng:Optional[float]=Field(None,ge=-180,le=180); radius_m:Optional[float]=Field(None,gt=0,le=50000); active:Optional[bool]=None
