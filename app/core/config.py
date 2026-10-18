from __future__ import annotations
import os
from datetime import datetime,timezone

MAX_FAILED_LOGINS=int(os.getenv('MAX_FAILED_LOGINS','5'))
LOCK_MINUTES=int(os.getenv('LOCK_MINUTES','15'))
ACCESS_TOKEN_MINUTES=int(os.getenv('ACCESS_TOKEN_MINUTES','60'))
REFRESH_TOKEN_DAYS=int(os.getenv('REFRESH_TOKEN_DAYS','14'))
REFRESH_REUSE_GRACE_SECONDS=int(os.getenv('REFRESH_REUSE_GRACE_SECONDS','20'))
def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ریشهٔ پروژه (کنار web/ و mobile/)
def _db_url(u):
 """Railway/Heroku آدرس را به شکل postgres:// یا postgresql:// می‌دهند؛ SQLAlchemy با درایور psycopg3 به postgresql+psycopg:// نیاز دارد"""
 for pre in ('postgres://','postgresql://'):
  if u.startswith(pre): return 'postgresql+psycopg://'+u[len(pre):]
 return u
DB_URL=_db_url(os.getenv('DATABASE_URL') or 'sqlite:///'+os.path.join(ROOT,'data.sqlite3'))
UPLOAD_DIR=os.getenv('UPLOAD_DIR') or os.path.join(ROOT,'uploads')   # روی Railway به مسیر Volume اشاره کنید (مثلاً /data/uploads)
web=os.path.join(ROOT,'web')
mobile=os.path.join(ROOT,'mobile')
REMINDER_INTERVAL_SECONDS=int(os.getenv('REMINDER_INTERVAL_SECONDS','900'))  # 0 = غیرفعال

# ---- مرحله ۱۶: API یکپارچه (مقادیر در هر درخواست از env خوانده می‌شوند تا تست/عملیات بتواند عوضشان کند)
def env_int(name,default):
 try: return int(os.getenv(name,str(default)))
 except ValueError: return default
def cors_origins(): return [o.strip().rstrip('/') for o in os.getenv('CORS_ORIGINS','').split(',') if o.strip()]
