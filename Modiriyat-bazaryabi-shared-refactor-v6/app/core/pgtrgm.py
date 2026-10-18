"""ایندکس‌های pg_trgm برای جستجوی سریع «شامل» (ILIKE '%x%') روی PostgreSQL؛ در SQLite هیچ‌کاری نمی‌کند.
هم در مایگریشن و هم هنگام راه‌اندازی (idempotent) اجرا می‌شود؛ نبود دسترسی CREATE EXTENSION خطا نمی‌دهد (فقط لاگ)."""
import logging
from sqlalchemy import text
TRGM=[('customers','name'),('customers','code'),('customers','phone'),('products','name'),('products','sku'),('orders','number'),('invoices','number'),('journal_entries','number'),('journal_entries','description')]
def apply(conn):
 if conn.dialect.name!='postgresql': return False
 try:
  with conn.begin_nested():
   conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
   for t,c in TRGM: conn.execute(text(f'CREATE INDEX IF NOT EXISTS ix_{t}_{c}_trgm ON {t} USING gin ({c} gin_trgm_ops)'))
  return True
 except Exception:
  logging.getLogger('abtin').warning('pg_trgm indexes were not created (extension/privilege missing); search still works without them',exc_info=True)
  return False

def status(conn):
 """وضعیت واقعی ایندکس‌ها برای نمایش به مدیر: {'dialect','extension','missing':[...],'ok'}"""
 if conn.dialect.name!='postgresql': return {'dialect':conn.dialect.name,'extension':False,'missing':[],'ok':True,'note':'روی SQLite نیازی به pg_trgm نیست'}
 ext=bool(conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")).scalar())
 have={r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes WHERE indexname LIKE '%_trgm'"))}
 miss=[f'ix_{t}_{c}_trgm' for t,c in TRGM if f'ix_{t}_{c}_trgm' not in have]
 return {'dialect':'postgresql','extension':ext,'missing':miss,'ok':ext and not miss,'fix_sql':['CREATE EXTENSION IF NOT EXISTS pg_trgm;']+[f'CREATE INDEX IF NOT EXISTS ix_{t}_{c}_trgm ON {t} USING gin ({c} gin_trgm_ops);' for t,c in TRGM] if not (ext and not miss) else []}
