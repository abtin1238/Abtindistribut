from __future__ import annotations
from fastapi import APIRouter, Request
from .service import root as _s_root, health as _s_health, ready as _s_ready, metrics_endpoint as _s_metrics_endpoint

router=APIRouter()

@router.get('/')
def root():
 return _s_root()

@router.get('/health')
@router.get('/api/health')
def health():
 return _s_health()

@router.get('/ready')
@router.get('/api/ready')
def ready():
 'آماده\u200cبه\u200cکار بودن (اتصال دیتابیس) برای load balancer / orchestrator'
 return _s_ready()

@router.get('/metrics',include_in_schema=False)
def metrics_endpoint(request: Request):
 'متریک Prometheus؛ فقط وقتی METRICS_TOKEN تنظیم شده و هدر Authorization: Bearer <token> درست باشد (وگرنه ۴۰۴)'
 return _s_metrics_endpoint(request=request)
