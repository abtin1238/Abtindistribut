from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from app.services.accounting import vat_percent
from app.services.files import sniff_type  # noqa: F401

class BrandingIn(BaseModel): name:str=Field('',max_length=60); tagline:str=Field('',max_length=100); color:str=Field('#2f7bff',pattern=r'^#[0-9a-fA-F]{6}$')

class TaxIn(BaseModel): vat_percent:Decimal=Field(ge=0,le=100)

class ThemeIn(BaseModel):
 color:str=Field(pattern=r'^#[0-9a-fA-F]{6}$');radius:int=Field(16,ge=6,le=28);font_scale:int=Field(100,ge=90,le=120);mode:str=Field('system',pattern=r'^(system|dark|light)$')
