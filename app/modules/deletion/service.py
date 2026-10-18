from __future__ import annotations
"""حذف یکپارچه (فقط مدیر کل): هر رکورد فقط وقتی حذف می‌شود که هیچ رکورد دیگری به آن وابسته نباشد.
فرزندان «مالکیتی» (ردیف فاکتور، فعالیت سرنخ و …) همراه والد حذف می‌شوند؛ اسناد مالی فقط در وضعیت پیش‌نویس/لغوشده."""
from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from app.core.common import audit
from app.core.database import Base
from app.core.security import is_super
from app.models import (Account, Attendance, BankAccount, Chequebook, Contract, Customer, CustomerAddress, CustomerContact, Delivery, Employee, FiscalPeriod,
 Invoice, InvoiceLine, JournalEntry, JournalLine, Lead, LeadActivity, LeaveRequest, Membership, Order, OrderItem, Product, Proposal, ProposalLine,
 Purchase, PurchaseItem, RefreshToken, Role, SessionToken, Shift, StockCount, StockCountLine, Supplier, Target, Task, User, Visit, VisitPlan, VisitPlanItem, Warehouse)

SAFE=('draft','cancelled')
# مسیر API → (مدل، فرزندان مالکیتی، مدل‌هایی که ارجاعشان فقط خالی می‌شود، وضعیت‌های مجاز برای حذف)
REGISTRY={
 'customers':(Customer,(CustomerAddress,CustomerContact),(),None),
 'leads':(Lead,(LeadActivity,),(Task,Proposal),None),
 'tasks':(Task,(),(),None),
 'proposals':(Proposal,(ProposalLine,),(),None),
 'targets':(Target,(),(),None),
 'visits':(Visit,(),(),None),
 'visit-plans':(VisitPlan,(VisitPlanItem,),(Visit,),None),
 'products':(Product,(),(),None),
 'warehouses':(Warehouse,(),(),None),
 'suppliers':(Supplier,(),(),None),
 'employees':(Employee,(),(),None),
 'attendance':(Attendance,(),(),None),
 'leaves':(LeaveRequest,(),(),None),
 'shifts':(Shift,(),(),None),
 'contracts':(Contract,(),(),None),
 'deliveries':(Delivery,(),(),None),
 'accounts':(Account,(),(),None),
 'bank-accounts':(BankAccount,(),(),None),
 'chequebooks':(Chequebook,(),(),None),
 'fiscal/periods':(FiscalPeriod,(),(),None),
 'stock/counts':(StockCount,(StockCountLine,),(),SAFE),
 'orders':(Order,(OrderItem,),(),SAFE),
 'invoices':(Invoice,(InvoiceLine,),(),SAFE),
 'purchases':(Purchase,(PurchaseItem,),(),SAFE),
 'journal':(JournalEntry,(JournalLine,),(),('draft',)),
}
LABELS={'users':'کاربر','roles':'نقش'}

def keys(ctx):
 if not is_super(ctx[2]): raise HTTPException(403,'فقط مدیر کل می‌تواند حذف کند')
 return sorted([*REGISTRY,'users','roles'])

def _cols(model,tables):
 """ستون‌های کلید خارجی که به جدول model اشاره می‌کنند؛ جدول‌های tables را شامل می‌شود"""
 out=[]
 for t in Base.metadata.sorted_tables:
  for fk in t.foreign_keys:
   if fk.column.table is model.__table__ and fk.column.name=='id' and t in tables: out.append(fk.parent)
 return out

def _blockers(s,model,rid,skip):
 """تعداد رکوردهای وابسته (جدول‌های skip حساب نمی‌شوند)"""
 res=[]
 for t in Base.metadata.sorted_tables:
  if t in skip or t is model.__table__: continue
  for fk in t.foreign_keys:
   if fk.column.table is model.__table__ and fk.column.name=='id':
    n=s.scalar(select(func.count()).select_from(t).where(fk.parent==rid)) or 0
    if n: res.append((t.name,n))
 return res

def _explain(bl):
 return 'به‌دلیل رکوردهای وابسته حذف نشد ('+'، '.join(f'{t}: {n}' for t,n in bl[:4])+')؛ ابتدا آن‌ها را حذف یا لغو کنید'

def remove(key:str,rid:int,ctx,s:Session):
 u,cid,r=ctx
 if not is_super(r): raise HTTPException(403,'فقط مدیر کل می‌تواند حذف کند')
 if key not in REGISTRY: raise HTTPException(404,'این بخش حذف‌پذیر نیست')
 model,owned,nullify,safe=REGISTRY[key]
 x=s.get(model,rid)
 if not x or getattr(x,'company_id',cid)!=cid: raise HTTPException(404,'مورد یافت نشد')
 if safe is not None and getattr(x,'status','draft') not in safe: raise HTTPException(409,'فقط پیش‌نویس یا لغوشده قابل حذف است؛ ابتدا لغو/معکوس کنید')
 skip={m.__table__ for m in (*owned,*nullify)}
 bl=_blockers(s,model,rid,skip)
 if bl: raise HTTPException(409,_explain(bl))
 for m in owned:
  for col in _cols(model,{m.__table__}): s.execute(delete(m).where(col==rid))
 for m in nullify:
  for col in _cols(model,{m.__table__}): s.execute(update(m).where(col==rid).values({col.name:None}))
 s.delete(x);audit(s,cid,u.id,'delete',key,rid);s.commit()
 return {'deleted':True,'id':rid}

def remove_role(rid:int,ctx,s:Session):
 u,cid,r=ctx;q=s.get(Role,rid)
 if not is_super(r): raise HTTPException(403,'فقط مدیر کل می‌تواند حذف کند')
 if not q or q.company_id!=cid: raise HTTPException(404,'نقش یافت نشد')
 if '*' in (q.permissions or []): raise HTTPException(409,'نقش مدیر کل قابل حذف نیست')
 n=s.scalar(select(func.count()).select_from(User).where(User.role_id==rid)) or 0
 if n: raise HTTPException(409,f'{n} کاربر این نقش را دارند؛ ابتدا نقش آن‌ها را عوض کنید')
 bl=_blockers(s,Role,rid,set())
 if bl: raise HTTPException(409,_explain(bl))
 s.delete(q);audit(s,cid,u.id,'delete','role',rid);s.commit();return {'deleted':True,'id':rid}

def remove_user(uid:int,ctx,s:Session):
 """کاربر از شرکت جاری حذف می‌شود. اگر سابقه‌ای دارد (فاکتور، گزارش فعالیت، …) برای حفظ تاریخچه ناشناس و غیرفعال می‌شود، وگرنه کامل پاک می‌شود"""
 u,cid,r=ctx;t=s.get(User,uid)
 if not is_super(r): raise HTTPException(403,'فقط مدیر کل می‌تواند حذف کند')
 if not t or not s.scalar(select(Membership).where(Membership.user_id==uid,Membership.company_id==cid)): raise HTTPException(404,'کاربر یافت نشد')
 if uid==u.id: raise HTTPException(400,'حذف حساب خودتان مجاز نیست')
 s.execute(delete(Membership).where(Membership.user_id==uid,Membership.company_id==cid))
 if s.scalar(select(func.count()).select_from(Membership).where(Membership.user_id==uid)):   # هنوز عضو شرکت دیگری است
  audit(s,cid,u.id,'delete','user',uid);s.commit();return {'deleted':True,'id':uid,'mode':'membership'}
 s.execute(delete(SessionToken).where(SessionToken.user_id==uid));s.execute(delete(RefreshToken).where(RefreshToken.user_id==uid))
 skip={SessionToken.__table__,RefreshToken.__table__,Membership.__table__}
 bl=_blockers(s,User,uid,skip)
 audit(s,cid,u.id,'delete','user',uid)
 if bl:
  t.active=False;t.username=f'deleted_{uid}';t.name=f'{t.name} (حذف‌شده)';mode='anonymized'
 else: s.delete(t);mode='deleted'
 s.commit();return {'deleted':True,'id':uid,'mode':mode}
