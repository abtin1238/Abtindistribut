from __future__ import annotations
from app.core.richtext import clean_html

def _rt(v): return clean_html(v) if isinstance(v,str) else v
