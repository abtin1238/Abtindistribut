from __future__ import annotations
from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session
from app.core.database import db
from app.core.security import current
from app.schemas import BranchIn, LoginIn, PasswordChangeIn, PasswordResetIn, MembershipIn, OrgIn, RoleIn, UserIn, UserPatch
from .service import refresh as _s_refresh, reset_password as _s_reset_password, logout as _s_logout, logout_all as _s_logout_all, my_sessions as _s_my_sessions, change_password as _s_change_password, login as _s_login, switch_company as _s_switch_company, me as _s_me, organizations as _s_organizations, users as _s_users, add_user as _s_add_user, roles as _s_roles, add_role as _s_add_role, add_membership as _s_add_membership, create_company as _s_create_company, create_branch as _s_create_branch, audit_log as _s_audit_log, permissions_list as _s_permissions_list, roles_templates as _s_roles_templates, put_role as _s_put_role, patch_user as _s_patch_user

router=APIRouter()

@router.post('/api/auth/logout')
def logout(request: Request, response: Response, ctx=Depends(current), auth: str=Header(None, alias='Authorization'), s: Session=Depends(db)):
 'نشست جاری را باطل می\u200cکند (کلید API نشست ندارد و بی\u200cاثر است)'
 return _s_logout(ctx=ctx, auth=auth, s=s, request=request, response=response)

@router.post('/api/auth/logout-all')
def logout_all(request: Request, ctx=Depends(current), auth: str=Header(None, alias='Authorization'), s: Session=Depends(db)):
 'همهٔ نشست\u200cهای دیگر کاربر را می\u200cبندد و نشست جاری را نگه می\u200cدارد'
 return _s_logout_all(ctx=ctx, auth=auth, s=s, request=request)

@router.get('/api/auth/sessions')
def my_sessions(ctx=Depends(current), auth: str=Header(None, alias='Authorization'), s: Session=Depends(db)):
 return _s_my_sessions(ctx=ctx, auth=auth, s=s)

@router.post('/api/auth/change-password')
def change_password(x: PasswordChangeIn, request: Request, ctx=Depends(current), auth: str=Header(None, alias='Authorization'), s: Session=Depends(db)):
 return _s_change_password(x=x, ctx=ctx, auth=auth, s=s, request=request)

@router.post('/api/auth/login')
def login(x: LoginIn, request: Request, response: Response, s: Session=Depends(db)):
 return _s_login(x=x, request=request, s=s, response=response)

@router.post('/api/auth/refresh')
def refresh(request: Request, response: Response, s: Session=Depends(db)):
 'refresh token (کوکی HttpOnly) را می‌چرخاند و access token تازه می‌دهد؛ هدر X-Requested-With: abtin الزامی است'
 return _s_refresh(request=request, response=response, s=s)

@router.post('/api/auth/switch-company')
def switch_company(company_id: int, request: Request, response: Response, ctx=Depends(current), s: Session=Depends(db)):
 return _s_switch_company(company_id=company_id, ctx=ctx, s=s, request=request, response=response)

@router.get('/api/me')
def me(ctx=Depends(current), s: Session=Depends(db)):
 return _s_me(ctx=ctx, s=s)

@router.get('/api/organizations')
def organizations(ctx=Depends(current), s: Session=Depends(db)):
 return _s_organizations(ctx=ctx, s=s)

@router.get('/api/users')
def users(ctx=Depends(current), s: Session=Depends(db)):
 return _s_users(ctx=ctx, s=s)

@router.post('/api/users')
def add_user(x: UserIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_user(x=x, ctx=ctx, s=s)

@router.get('/api/roles')
def roles(ctx=Depends(current), s: Session=Depends(db)):
 return _s_roles(ctx=ctx, s=s)

@router.post('/api/roles')
def add_role(x: RoleIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_role(x=x, ctx=ctx, s=s)

@router.post('/api/memberships')
def add_membership(x: MembershipIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_membership(x=x, ctx=ctx, s=s)

@router.post('/api/organizations/company')
def create_company(x: OrgIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_company(x=x, ctx=ctx, s=s)

@router.post('/api/organizations/branch')
def create_branch(x: BranchIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_create_branch(x=x, ctx=ctx, s=s)

@router.get('/api/audit')
def audit_log(ctx=Depends(current), s: Session=Depends(db)):
 return _s_audit_log(ctx=ctx, s=s)

@router.get('/api/permissions')
def permissions_list(ctx=Depends(current)):
 return _s_permissions_list(ctx=ctx)

@router.post('/api/roles/templates')
def roles_templates(ctx=Depends(current), s: Session=Depends(db)):
 return _s_roles_templates(ctx=ctx, s=s)

@router.put('/api/roles/{rid}')
def put_role(rid: int, x: RoleIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_put_role(rid=rid, x=x, ctx=ctx, s=s)

@router.patch('/api/users/{uid}')
def patch_user(uid: int, x: UserPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_patch_user(uid=uid, x=x, ctx=ctx, s=s)

@router.post('/api/users/{uid}/reset-password')
def reset_password(uid: int, x: PasswordResetIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_reset_password(uid=uid, x=x, ctx=ctx, s=s)
