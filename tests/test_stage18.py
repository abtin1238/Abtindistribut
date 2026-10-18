"""مرحله ۱۸ — سخت‌سازی و عملیات: سیاست رمز ادمین، هدرهای امنیتی/HSTS، متریک Prometheus با توکن"""
import os
os.environ['DATABASE_URL']='sqlite:////tmp/abtin_dist_stage18.sqlite3'
os.environ['ADMIN_PASSWORD']='test-password'
os.environ['METRICS_TOKEN']='m-secret-token'
try: os.remove('/tmp/abtin_dist_stage18.sqlite3')
except FileNotFoundError: pass
import pytest
from fastapi.testclient import TestClient
from app.core import metrics
from app.core.bootstrap import admin_password,password_is_weak
from app.main import app
client=TestClient(app)

@pytest.mark.parametrize('pw',['','change-me','change-me-strong','Change-Me-Please','admin','Admin@12345','password'])
def test_placeholder_passwords_are_weak(pw): assert password_is_weak(pw,False)
def test_production_requires_12_chars():
    assert password_is_weak('short-pw',True) and not password_is_weak('short-pw',False)
    assert not password_is_weak('a-real-long-password-9',True)
def test_production_rejects_weak_admin_password(monkeypatch):
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('ADMIN_PASSWORD','change-me')
    with pytest.raises(RuntimeError): admin_password()
def test_dev_weak_password_gets_generated(monkeypatch,capsys):
    monkeypatch.delenv('APP_ENV',raising=False);monkeypatch.setenv('ADMIN_PASSWORD','change-me')
    pw=admin_password();assert pw!='change-me' and len(pw)>=14

def test_security_headers_and_hsts_only_on_https():
    r=client.get('/api/health')
    assert r.headers['X-Content-Type-Options']=='nosniff' and r.headers['X-Frame-Options']=='DENY'
    assert 'frame-ancestors' in r.headers['Content-Security-Policy']
    assert r.headers['Cache-Control']=='no-store' and 'Strict-Transport-Security' not in r.headers
    r=client.get('/api/health',headers={'X-Forwarded-Proto':'https'})
    assert 'max-age=31536000' in r.headers['Strict-Transport-Security']

def test_metrics_requires_token():
    assert client.get('/metrics').status_code==404
    assert client.get('/metrics',headers={'Authorization':'Bearer wrong'}).status_code==404
def test_metrics_counts_requests_by_route_template():
    metrics.reset();client.get('/api/health');client.get('/api/health');client.get('/api/does-not-exist')
    r=client.get('/metrics',headers={'Authorization':'Bearer m-secret-token'})
    assert r.status_code==200 and 'text/plain' in r.headers['content-type']
    assert 'abtin_http_requests_total{method="GET",path="/api/health",status_class="2xx"} 2' in r.text
    assert 'abtin_http_request_duration_seconds_count{method="GET",path="/api/health"} 2' in r.text
    assert 'abtin_process_uptime_seconds' in r.text

def test_metrics_registry_pure():
    metrics.reset();metrics.observe('GET','/x',200,0.03);metrics.observe('GET','/x',500,3.0)
    t=metrics.render()
    assert 'abtin_http_requests_total{method="GET",path="/x",status_class="5xx"} 1' in t
    assert 'le="0.05"} 1' in t and 'le="+Inf"} 2' in t and 'duration_seconds_count{method="GET",path="/x"} 2' in t
