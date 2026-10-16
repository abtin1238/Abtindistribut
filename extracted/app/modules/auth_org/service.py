from __future__ import annotations
import hashlib
import secrets
from datetime import timedelta
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session
from app.core.common import audit, obj
from app.core.config import ACCESS_TOKEN_MINUTES, LOCK_MINUTES, MAX_FAILED_LOGINS, REFRESH_REUSE_GRACE_SECONDS, REFRESH_TOKEN_DAYS, utcnow
from app.core.security import ALL_PERMS, check_codes, checkpw, ensure_templates, granted, hashpw
from app.models import Audit, Branch, Company, Group, Membership, RefreshToken, Role, SessionToken, User
from app.core.bootstrap import password_is_weak
from .schemas import LoginIn, PasswordChangeIn, OrgIn, BranchIn, UserIn, RoleIn, MembershipIn, UserPatch, PasswordResetIn, PasswordResetIn

def _ip(request):
 from app.core.ratelimit import client_ip
 return client_ip(request)[:64]

def _cur_token(auth):
 return auth[7:] if auth and auth.startswith('Bearer ') else None

COOKIE='abtin_rt'

def _hash(t): return hashlib.sha256(t.encode()).hexdigest()

def _set_cookie(response,request,raw):
 """refresh token فقط در کوکی HttpOnly؛ SameSite=Strict (CSRF) و Secure روی HTTPS"""
 https=request.url.scheme=='https' or (request.headers.get('x-forwarded-proto') or '').split(',')[0].strip()=='https'
 response.set_cookie(COOKIE,raw,max_age=REFRESH_TOKEN_DAYS*86400,httponly=True,secure=https,samesite='strict',path='/api')

def _clear_cookie(response): response.delete_cookie(COOKIE,path='/api')

def _new_session(s,u,cid,request):
 tok=secrets.token_urlsafe(48); now=utcnow()
 s.add(SessionToken(token=tok,user_id=u.id,company_id=cid,expires_at=now+timedelta(minutes=ACCESS_TOKEN_MINUTES),created_at=now,ip=_ip(request),user_agent=(request.headers.get('user-agent') or '')[:300]))
 return tok

def _new_refresh(s,u,cid,request,session_token,family=None):
 raw=secrets.token_urlsafe(48); now=utcnow()
 s.add(RefreshToken(token_hash=_hash(raw),family=family or secrets.token_hex(16),user_id=u.id,company_id=cid,session_token=session_token,expires_at=now+timedelta(days=REFRESH_TOKEN_DAYS),created_at=now,ip=_ip(request),user_agent=(request.headers.get('user-agent') or '')[:300]))
 return raw

def _revoke_refresh(s,user_id,keep_family=None):
 """همه‌ی refreshهای فعال کاربر را باطل می‌کند (به‌جز یک خانواده‌ی اختیاری)؛ تعداد را برمی‌گرداند"""
 q=update(RefreshToken).where(RefreshToken.user_id==user_id,RefreshToken.revoked_at==None)
 if keep_family: q=q.where(RefreshToken.family!=keep_family)
 return s.execute(q.values(revoked_at=utcnow())).rowcount

def _family_of(s,request):
 raw=request.cookies.get(COOKIE)
 if not raw: return None
 r=s.scalar(select(RefreshToken).where(RefreshToken.token_hash==_hash(raw))); return r.family if r else None

def refresh(request: Request, response: Response, s: Session):
 """چرخش refresh token: توکن قدیمی باطل، یک refresh و access تازه صادر می‌شود. استفاده‌ی مجدد از توکن باطل‌شده (خارج از مهلت رقابت چندتب) کل خانواده را می‌بندد."""
 if request.headers.get('x-requested-with')!='abtin': raise HTTPException(400,'هدر X-Requested-With الزامی است')
 raw=request.cookies.get(COOKIE)
 if not raw: raise HTTPException(401,'نشست یافت نشد؛ دوباره وارد شوید')
 r=s.scalar(select(RefreshToken).where(RefreshToken.token_hash==_hash(raw)))
 bad=HTTPException(401,'نشست منقضی شده است؛ دوباره وارد شوید')
 now=utcnow()
 if not r: _clear_cookie(response); raise bad
 if r.revoked_at:
  if (now-r.revoked_at).total_seconds()>REFRESH_REUSE_GRACE_SECONDS:
   s.execute(update(RefreshToken).where(RefreshToken.family==r.family,RefreshToken.revoked_at==None).values(revoked_at=now))
   s.execute(delete(SessionToken).where(SessionToken.user_id==r.user_id,SessionToken.token.in_(select(RefreshToken.session_token).where(RefreshToken.family==r.family))))
   audit(s,r.company_id,r.user_id,'refresh_reuse_detected','user',r.user_id,{'ip':_ip(request)}); s.commit()
  raise bad
 if r.expires_at<now: raise bad
 u=s.get(User,r.user_id)
 if not u or not u.active or not s.scalar(select(Membership).where(Membership.user_id==u.id,Membership.company_id==r.company_id)): raise bad
 # ادعای اتمی: فقط یک درخواست همزمان برنده می‌شود
 if not s.execute(update(RefreshToken).where(RefreshToken.id==r.id,RefreshToken.revoked_at==None).values(revoked_at=now)).rowcount: s.rollback(); raise bad
 if r.session_token: s.execute(delete(SessionToken).where(SessionToken.token==r.session_token))
 tok=_new_session(s,u,r.company_id,request); nr=_new_refresh(s,u,r.company_id,request,tok,family=r.family)
 s.commit(); _set_cookie(response,request,nr)
 return {'token':tok,'expires_in':ACCESS_TOKEN_MINUTES*60,'company_id':r.company_id}

def logout(ctx, auth: str, s: Session, request: Request=None, response: Response=None):
 """نشست جاری و refresh token آن را باطل می‌کند (کلید API نشست ندارد و بی‌اثر است)"""
 t=_cur_token(auth)
 if request is not None:
  fam=_family_of(s,request)
  if fam: s.execute(update(RefreshToken).where(RefreshToken.family==fam,RefreshToken.user_id==ctx[0].id,RefreshToken.revoked_at==None).values(revoked_at=utcnow())); s.commit()
 if response is not None: _clear_cookie(response)
 if t and not t.startswith('abk_'): s.execute(delete(SessionToken).where(SessionToken.token==t,SessionToken.user_id==ctx[0].id)); audit(s,ctx[1],ctx[0].id,'logout','user',ctx[0].id,{}); s.commit()
 return {'ok':True}

def logout_all(ctx, auth: str, s: Session, request: Request=None):
 """همهٔ نشست‌های دیگر کاربر را می‌بندد (access و refresh) و نشست جاری را نگه می‌دارد"""
 _revoke_refresh(s,ctx[0].id,keep_family=_family_of(s,request) if request is not None else None)
 t=_cur_token(auth); n=s.execute(delete(SessionToken).where(SessionToken.user_id==ctx[0].id,SessionToken.token!=(t or ''))).rowcount
 audit(s,ctx[1],ctx[0].id,'logout_all','user',ctx[0].id,{'revoked':n}); s.commit(); return {'revoked':n}

def my_sessions(ctx, auth: str, s: Session):
 t=_cur_token(auth); rows=s.scalars(select(SessionToken).where(SessionToken.user_id==ctx[0].id,SessionToken.expires_at>utcnow()).order_by(SessionToken.expires_at.desc())).all()
 return [{'id':x.token[:8],'created_at':x.created_at.isoformat() if x.created_at else None,'expires_at':x.expires_at.isoformat(),'ip':x.ip,'user_agent':x.user_agent,'current':x.token==t} for x in rows]

def _check_password_policy(pw,username):
 import os
 if len(pw)<8 or password_is_weak(pw,os.getenv('APP_ENV','').lower()=='production') or pw.lower()==username.lower(): raise HTTPException(400,'رمز ضعیف است (حداقل ۸ نویسه؛ در production حداقل ۱۲ و نباید نمونه/نام‌کاربری باشد)')

def change_password(x: PasswordChangeIn, ctx, auth: str, s: Session, request: Request=None):
 import os
 u=ctx[0]
 if not checkpw(x.old_password,u.password_hash): raise HTTPException(400,'رمز فعلی نادرست است')
 if x.new_password==x.old_password: raise HTTPException(400,'رمز جدید باید با رمز فعلی متفاوت باشد')
 if len(x.new_password)<8 or password_is_weak(x.new_password,os.getenv('APP_ENV','').lower()=='production') or x.new_password.lower()==u.username.lower(): raise HTTPException(400,'رمز جدید ضعیف است (حداقل ۸ نویسه؛ در production حداقل ۱۲ و نباید نمونه/نام‌کاربری باشد)')
 u=s.get(User,u.id); u.password_hash=hashpw(x.new_password); t=_cur_token(auth)
 _revoke_refresh(s,u.id,keep_family=_family_of(s,request) if request is not None else None)
 n=s.execute(delete(SessionToken).where(SessionToken.user_id==u.id,SessionToken.token!=(t or ''))).rowcount
 audit(s,ctx[1],u.id,'password_change','user',u.id,{'sessions_revoked':n}); s.commit(); return {'ok':True,'sessions_revoked':n}

def login(x: LoginIn, request: Request, s: Session, response: Response=None):
 u=s.scalar(select(User).where(User.username==x.username))
 if u and u.locked_until and u.locked_until>utcnow(): raise HTTPException(429,'حساب به‌دلیل تلاش‌های ناموفق موقتاً قفل شده است؛ بعداً تلاش کنید')
 if not u or not checkpw(x.password,u.password_hash) or not u.active:
  if u:
   u.failed_attempts=(u.failed_attempts or 0)+1
   if u.failed_attempts>=MAX_FAILED_LOGINS: u.locked_until=utcnow()+timedelta(minutes=LOCK_MINUTES);u.failed_attempts=0
   s.commit()
  raise HTTPException(401,'نام کاربری یا رمز عبور نادرست است')
 u.failed_attempts=0;u.locked_until=None
 memberships=s.scalars(select(Membership).where(Membership.user_id==u.id)).all()
 allowed={m.company_id for m in memberships}
 cid=x.company_id or next((m.company_id for m in memberships if m.is_default),None)
 if cid not in allowed: raise HTTPException(403,'شرکت انتخابی برای کاربر مجاز نیست')
 token=_new_session(s,u,cid,request); rt=_new_refresh(s,u,cid,request,token); audit(s,cid,u.id,'login','user',u.id,{'ip':_ip(request)}); s.commit()
 if response is not None: _set_cookie(response,request,rt)
 return {'token':token,'expires_in':ACCESS_TOKEN_MINUTES*60,'company_id':cid}

def switch_company(company_id: int, ctx, s: Session, request: Request=None, response: Response=None):
 u,_,_=ctx
 if not s.scalar(select(Membership).where(Membership.user_id==u.id,Membership.company_id==company_id)): raise HTTPException(403,'دسترسی به شرکت وجود ندارد')
 if request is None: token=secrets.token_urlsafe(48); s.add(SessionToken(token=token,user_id=u.id,company_id=company_id,expires_at=utcnow()+timedelta(minutes=ACCESS_TOKEN_MINUTES))); s.commit(); return {'token':token,'company_id':company_id}
 fam=_family_of(s,request)
 if fam: s.execute(update(RefreshToken).where(RefreshToken.family==fam,RefreshToken.user_id==u.id,RefreshToken.revoked_at==None).values(revoked_at=utcnow()))
 token=_new_session(s,u,company_id,request); rt=_new_refresh(s,u,company_id,request,token); audit(s,company_id,u.id,'switch_company','user',u.id,{}); s.commit()
 if response is not None: _set_cookie(response,request,rt)
 return {'token':token,'expires_in':ACCESS_TOKEN_MINUTES*60,'company_id':company_id}

def me(ctx, s: Session):
 u,cid,r=ctx; c=s.get(Company,cid); g=s.get(Group,c.group_id); memberships=s.scalars(select(Membership).where(Membership.user_id==u.id)).all(); companies=[s.get(Company,m.company_id) for m in memberships]; return {'user':{'id':u.id,'name':u.name,'username':u.username,'role':r.name,'permissions':r.permissions},'company':{'id':c.id,'name':c.name,'code':c.code,'group_name':g.name},'companies':[{'id':x.id,'name':x.name,'code':x.code} for x in companies if x]}

def organizations(ctx, s: Session):
 c=s.get(Company,ctx[1]); cs=s.scalars(select(Company).where(Company.group_id==c.group_id)).all(); bs=s.scalars(select(Branch).where(Branch.company_id.in_([x.id for x in cs]))).all(); return {'group':obj(s.get(Group,c.group_id)),'companies':[obj(x) for x in cs],'branches':[obj(x) for x in bs]}

def users(ctx, s: Session):
 u,cid,r=ctx
 ids=[m.user_id for m in s.scalars(select(Membership).where(Membership.company_id==cid)).all()]
 return [{k:v for k,v in obj(x).items() if k!='password_hash'} for x in s.scalars(select(User).where(User.id.in_(ids))).all()]

def add_user(x: UserIn, ctx, s: Session):
 u,cid,r=ctx
 if s.scalar(select(User).where(User.username==x.username)): raise HTTPException(409,'نام کاربری تکراری است')
 _check_password_policy(x.password,x.username)
 role=s.get(Role,x.role_id)
 if not role or role.company_id not in (None,cid): raise HTTPException(404,'نقش یافت نشد')
 if not granted(r,role.permissions or []): raise HTTPException(403,'نمی‌توانید نقشی با دسترسی بیشتر از خودتان بدهید')
 if '*' not in (r.permissions or []) and not set(x.company_ids)<={mm.company_id for mm in s.scalars(select(Membership).where(Membership.user_id==u.id))}: raise HTTPException(403,'دسترسی شرکت غیرمجاز')
 if x.branch_id is not None:
  b=s.get(Branch,x.branch_id)
  if not b or b.company_id!=cid: raise HTTPException(404,'شعبه یافت نشد')
 q=User(username=x.username,password_hash=hashpw(x.password),name=x.name,role_id=x.role_id);s.add(q);s.flush()
 company_ids=x.company_ids or [cid]
 for target in company_ids:
  if not s.get(Company,target): raise HTTPException(404,'شرکت یافت نشد')
  s.add(Membership(user_id=q.id,company_id=target,is_default=(target==cid),branch_id=x.branch_id if target==cid else None))
 audit(s,cid,u.id,'create','user',q.id);s.commit();s.refresh(q);return {k:v for k,v in obj(q).items() if k!='password_hash'}

def roles(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(Role).where(or_(Role.company_id == ctx[1], Role.company_id == None))).all()]

def add_role(x: RoleIn, ctx, s: Session):
 u,cid,r=ctx; target=x.company_id or cid
 if target!=cid and '*' not in (r.permissions or []): raise HTTPException(403,'دسترسی شرکت غیرمجاز')
 check_codes(x.permissions)
 if not granted(r,x.permissions): raise HTTPException(403,'نمی‌توانید دسترسی بیشتر از خودتان بدهید')
 q=Role(company_id=target,name=x.name,permissions=x.permissions,max_discount_percent=x.max_discount_percent);s.add(q);audit(s,cid,u.id,'create','role');s.commit();s.refresh(q);return obj(q)

def add_membership(x: MembershipIn, ctx, s: Session):
 u,cid,r=ctx
 if x.company_id!=cid and '*' not in (r.permissions or []): raise HTTPException(403,'دسترسی شرکت غیرمجاز')
 if not s.get(User,x.user_id) or not s.get(Company,x.company_id): raise HTTPException(404,'کاربر یا شرکت یافت نشد')
 q=Membership(**x.model_dump());s.add(q);audit(s,cid,u.id,'create','membership',q.id);s.commit();s.refresh(q);return obj(q)

def create_company(x: OrgIn, ctx, s: Session):
 u,cid,r=ctx; parent=s.get(Company,x.parent_company_id) if x.parent_company_id else None; base=s.get(Company,cid)
 if parent and parent.group_id!=base.group_id: raise HTTPException(400,'شرکت والد باید در همان گروه باشد')
 c=Company(group_id=base.group_id,name=x.name,code=x.code,parent_company_id=x.parent_company_id);s.add(c);s.flush();s.add(Membership(user_id=u.id,company_id=c.id,is_default=False));audit(s,cid,u.id,'create','company',c.id,x.model_dump());s.commit();return obj(c)

def create_branch(x: BranchIn, ctx, s: Session):
 u,cid,r=ctx; target=s.get(Company,x.company_id)
 if not target: raise HTTPException(404,'شرکت یافت نشد')
 if target.id!=cid and '*' not in (r.permissions or []): raise HTTPException(403,'دسترسی شرکت غیرمجاز')
 b=Branch(**x.model_dump());s.add(b);audit(s,cid,u.id,'create','branch',None,x.model_dump());s.commit();s.refresh(b);return obj(b)

def audit_log(ctx, s: Session):
 return [obj(x) for x in s.scalars(select(Audit).where(Audit.company_id == ctx[1]).order_by(Audit.id.desc()).limit(1000)).all()]

def permissions_list(ctx):
 return sorted(ALL_PERMS)

def roles_templates(ctx, s: Session):
 ensure_templates(s, ctx[1])
 return [obj(x) for x in s.scalars(select(Role).where(Role.company_id == ctx[1]))]

def put_role(rid: int, x: RoleIn, ctx, s: Session):
 u,cid,r=ctx;q=s.get(Role,rid)
 if not q or q.company_id!=cid: raise HTTPException(404,'نقش یافت نشد')
 check_codes(x.permissions)
 if not granted(r,q.permissions or []) or not granted(r,x.permissions): raise HTTPException(403,'نمی‌توانید دسترسی بیشتر از خودتان بدهید یا نقش بالاتر را تغییر دهید')
 q.name=x.name;q.permissions=x.permissions;q.max_discount_percent=x.max_discount_percent;audit(s,cid,u.id,'update','role',q.id,x.model_dump());s.commit();return obj(q)

def reset_password(uid: int, x: PasswordResetIn, ctx, s: Session):
 """بازنشانی رمز توسط مدیر: رمز جدید باید سیاست را رعایت کند؛ همه‌ی نشست‌های کاربر باطل می‌شود"""
 u,cid,r=ctx;t=s.get(User,uid)
 if not t or not s.scalar(select(Membership).where(Membership.user_id==uid,Membership.company_id==cid)): raise HTTPException(404,'کاربر یافت نشد')
 if uid==u.id: raise HTTPException(400,'رمز خودتان را از «تغییر رمز» عوض کنید')
 if not granted(r,s.get(Role,t.role_id).permissions or []): raise HTTPException(403,'این کاربر دسترسی بالاتر از شما دارد')
 _check_password_policy(x.new_password,t.username)
 t.password_hash=hashpw(x.new_password); t.failed_attempts=0; t.locked_until=None
 n=s.execute(delete(SessionToken).where(SessionToken.user_id==uid)).rowcount; _revoke_refresh(s,uid)
 audit(s,cid,u.id,'password_reset','user',uid,{'sessions_revoked':n}); s.commit(); return {'ok':True,'sessions_revoked':n}

def patch_user(uid: int, x: UserPatch, ctx, s: Session):
 u,cid,r=ctx;t=s.get(User,uid)
 if not t or not s.scalar(select(Membership).where(Membership.user_id==uid,Membership.company_id==cid)): raise HTTPException(404,'کاربر یافت نشد')
 if uid==u.id: raise HTTPException(400,'تغییر نقش یا وضعیت خودتان مجاز نیست')
 if not granted(r,s.get(Role,t.role_id).permissions or []): raise HTTPException(403,'این کاربر دسترسی بالاتر از شما دارد')
 if x.role_id is not None:
  role=s.get(Role,x.role_id)
  if not role or role.company_id not in (None,cid): raise HTTPException(404,'نقش یافت نشد')
  if not granted(r,role.permissions or []): raise HTTPException(403,'نمی‌توانید نقشی با دسترسی بیشتر از خودتان بدهید')
  t.role_id=role.id
 if x.active is not None:
  t.active=x.active
  if not x.active: s.execute(delete(SessionToken).where(SessionToken.user_id==uid)); _revoke_refresh(s,uid)
 audit(s,cid,u.id,'update','user',uid,x.model_dump());s.commit();return {k:v for k,v in obj(t).items() if k!='password_hash'}
