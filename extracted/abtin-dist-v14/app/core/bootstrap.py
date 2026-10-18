from __future__ import annotations
import os
import secrets
from sqlalchemy import func,inspect,select,text
from app.core.database import Base,SessionLocal,engine
from app.core.security import hashpw
from app.models import Branch,Company,Group,Membership,Role,User,Warehouse

def ensure_schema():
 Base.metadata.create_all(engine)
 insp=inspect(engine)
 additions={'roles':{'max_discount_percent':'NUMERIC(5,2)'},'stock_transfer_batches':{'product_id':'INTEGER'},'audit_logs':{'ip':'VARCHAR(64)','request_id':'VARCHAR(64)'},'price_rules':{'min_qty':'NUMERIC(18,3) NOT NULL DEFAULT 1'},'sessions':{'created_at':'TIMESTAMP','ip':'VARCHAR(64)','user_agent':'VARCHAR(300)'},'products':{'avg_cost':'NUMERIC(18,4) NOT NULL DEFAULT 0','barcode':'VARCHAR(64)'},'stock_moves':{'unit_cost':'NUMERIC(18,4)'},'purchases':{'received_value':'NUMERIC(18,2) NOT NULL DEFAULT 0','discount':'NUMERIC(18,2) NOT NULL DEFAULT 0','freight':'NUMERIC(18,2) NOT NULL DEFAULT 0'},'purchase_items':{'received_qty':'NUMERIC(18,3) NOT NULL DEFAULT 0','returned_qty':'NUMERIC(18,3) NOT NULL DEFAULT 0','discount':'NUMERIC(18,2) NOT NULL DEFAULT 0','landed':'NUMERIC(18,2) NOT NULL DEFAULT 0'},'invoice_lines':{'unit_cost':'NUMERIC(18,4) NOT NULL DEFAULT 0','cogs':'NUMERIC(18,2) NOT NULL DEFAULT 0'},'branches':{'active':'BOOLEAN NOT NULL DEFAULT 1'},'warehouses':{'active':'BOOLEAN NOT NULL DEFAULT 1'},'orders':{'shipping':'NUMERIC(18,2) NOT NULL DEFAULT 0','note':"TEXT NOT NULL DEFAULT ''"},'invoices':{'note':"TEXT NOT NULL DEFAULT ''",'terms':"TEXT NOT NULL DEFAULT ''",'returned':'NUMERIC(18,2) NOT NULL DEFAULT 0','subtotal':'NUMERIC(18,2) NOT NULL DEFAULT 0','tax':'NUMERIC(18,2) NOT NULL DEFAULT 0','shipping':'NUMERIC(18,2) NOT NULL DEFAULT 0'},'customers':{'branch_id':'INTEGER','customer_group':"VARCHAR(100) NOT NULL DEFAULT ''"},'users':{'failed_attempts':'INTEGER NOT NULL DEFAULT 0','locked_until':'TIMESTAMP','email':"VARCHAR(200) NOT NULL DEFAULT ''",'phone':"VARCHAR(30) NOT NULL DEFAULT ''"},'notifications':{'event':"VARCHAR(40) NOT NULL DEFAULT ''",'entity':"VARCHAR(30) NOT NULL DEFAULT ''",'entity_id':'INTEGER','dedupe_key':'VARCHAR(100)'},'documents':{'owner_id':'INTEGER','size':'INTEGER NOT NULL DEFAULT 0','mime':"VARCHAR(100) NOT NULL DEFAULT ''",'sha256':"VARCHAR(64) NOT NULL DEFAULT ''",'restricted':'BOOLEAN NOT NULL DEFAULT FALSE','current_version':'INTEGER NOT NULL DEFAULT 1','deleted_at':'TIMESTAMP'},'journal_entries':{'source_type':'VARCHAR(40)','source_id':'INTEGER','reverses_id':'INTEGER','created_by':'INTEGER'},'checks':{'customer_id':'INTEGER','supplier_id':'INTEGER','endorsed_supplier_id':'INTEGER','endorsed_at':'TIMESTAMP','bank_account_id':'INTEGER','chequebook_id':'INTEGER'},'payments':{'bank_account_id':'INTEGER'},'sync_events':{'status':"VARCHAR(20) NOT NULL DEFAULT 'applied'",'error':"TEXT NOT NULL DEFAULT ''",'result_id':'INTEGER'}}
 with engine.begin() as conn:
  for table,cols in additions.items():
   existing={c['name'] for c in insp.get_columns(table)} if insp.has_table(table) else set()
   for name,ddl in cols.items():
    if name not in existing: conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
  from app.core import pgtrgm
  pgtrgm.apply(conn)
WEAK_ADMIN_PASSWORDS={'change-this','change-me','change-me-strong','change-me-before-production','admin','admin123','Admin@12345','password','12345678'}
def password_is_weak(pw:str,production:bool)->bool:
 """رمز خالی/نمونه/placeholder ضعیف است؛ در production حداقل ۱۲ نویسه هم لازم است"""
 low=pw.lower()
 return (not pw) or low in {w.lower() for w in WEAK_ADMIN_PASSWORDS} or low.startswith('change-me') or (production and len(pw)<12)
def admin_password():
 pw=os.getenv('ADMIN_PASSWORD','').strip()
 production=os.getenv('APP_ENV','').lower()=='production'
 if password_is_weak(pw,production):
  if pw and production: raise RuntimeError('ADMIN_PASSWORD ضعیف یا placeholder است؛ در production یک رمز ۱۲+ نویسه‌ای واقعی تنظیم کنید (scripts/gen-secrets.sh)')
  pw=secrets.token_urlsafe(14); print(f'[SETUP] ADMIN_PASSWORD not set/weak; generated one-time admin password: {pw}',flush=True)
 return pw
def seed():
 ensure_schema(); s=SessionLocal()
 if s.scalar(select(func.count()).select_from(Group))==0:
  g=Group(name='گروه نمونه'); s.add(g); s.flush(); c=Company(group_id=g.id,name='شرکت پخش نمونه',code='DIST-001'); s.add(c); s.flush(); b=Branch(company_id=c.id,name='شعبه مرکزی',address='تهران'); s.add(b); s.flush(); role=Role(company_id=c.id,name='مدیر کل',permissions=['*']); s.add(role); s.flush()
  if os.getenv('ADMIN_PASSWORD','').strip():   # روش قدیمی: ادمین از روی متغیر محیطی؛ بدون آن، مدیر کل در اولین ورود از صفحهٔ «راه‌اندازی» تعریف می‌شود
   u=User(username='admin',password_hash=hashpw(admin_password()),name='مدیر سیستم',role_id=role.id); s.add(u); s.flush(); s.add(Membership(user_id=u.id,company_id=c.id,branch_id=b.id,is_default=True))
  s.add(Warehouse(company_id=c.id,branch_id=b.id,name='انبار مرکزی',address='تهران')); s.commit()
 s.close()
