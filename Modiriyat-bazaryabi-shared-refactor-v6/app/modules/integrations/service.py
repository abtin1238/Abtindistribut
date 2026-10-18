from __future__ import annotations
import secrets
from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.core.common import audit, same_company
from app.core.config import utcnow
from app.core.paging import page_rows
from app.core.security import granted, need
from app.models import ApiKey, Role, WebhookDelivery, WebhookEndpoint
from app.services import webhooks as wh
from .schemas import ApiKeyIn, WebhookIn, WebhookPatch
import hashlib

def _humans_only(request:Request):
 if getattr(request.state,'api_key_id',None): raise HTTPException(403,'مدیریت کلید API/وبهوک با کلید API ممکن نیست')

def key_view(k:ApiKey): return {'id':k.id,'name':k.name,'prefix':k.prefix,'role_id':k.role_id,'created_by':k.created_by,'created_at':k.created_at,'expires_at':k.expires_at,'last_used_at':k.last_used_at,'revoked_at':k.revoked_at,'active':k.revoked_at is None and (k.expires_at is None or k.expires_at>utcnow())}

def hash_secret(secret:str)->str: return hashlib.sha256(secret.encode()).hexdigest()

def _events(ev):
 bad=[e for e in ev if e!='*' and (e not in wh.EVENTS or e=='webhook.test')]
 if bad: raise HTTPException(400,'رویداد نامعتبر: '+', '.join(bad))
 return sorted(set(ev))

def _url(url):
 try: return wh.check_url(url)
 except wh.UrlRejected as e: raise HTTPException(400,str(e))

def ep_view(e:WebhookEndpoint,secret=False):
 d={'id':e.id,'url':e.url,'events':e.events,'active':e.active,'consecutive_failures':e.consecutive_failures,'created_at':e.created_at,'secret_hint':'…'+e.secret[-4:]}
 if secret: d['secret']=e.secret
 return d

def _ep(s,ctx,eid): return same_company(s,WebhookEndpoint,eid,ctx[1])

MAX_TEST_ATTEMPT=wh.MAX_ATTEMPTS-1   # یک تلاش → نتیجه‌ی نهایی (failed یا delivered)

def list_keys(request: Request, ctx, s: Session):
 _humans_only(request);return [key_view(k) for k in s.scalars(select(ApiKey).where(ApiKey.company_id==ctx[1]).order_by(ApiKey.id.desc()))]

def create_key(x: ApiKeyIn, request: Request, ctx, s: Session):
 """کلید کامل فقط همین یک‌بار نمایش داده می‌شود. نقش کلید نباید از دسترسی سازنده بیشتر باشد."""
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write')
 role=same_company(s,Role,x.role_id,cid)
 if not granted(r,role.permissions or []): raise HTTPException(403,'نقش انتخابی از دسترسی‌های شما بیشتر است')
 prefix='abk_'+secrets.token_hex(4);secret=secrets.token_urlsafe(32)
 k=ApiKey(company_id=cid,name=x.name.strip(),prefix=prefix,key_hash=hash_secret(secret),role_id=role.id,created_by=u.id,expires_at=utcnow()+timedelta(days=x.expires_in_days) if x.expires_in_days else None)
 s.add(k);s.flush();audit(s,cid,u.id,'create','api_key',k.id,{'name':k.name,'role_id':role.id,'prefix':prefix});s.commit()
 return {**key_view(k),'key':f'{prefix}_{secret}'}

def revoke_key(kid: int, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;k=same_company(s,ApiKey,kid,cid)
 if k.revoked_at is None: k.revoked_at=utcnow();audit(s,cid,u.id,'revoke','api_key',k.id,{'prefix':k.prefix});s.commit()
 return key_view(k)

def webhook_events(ctx):
 return [{'event': k, 'title': v} for k, v in wh.EVENTS.items() if k != 'webhook.test']

def list_webhooks(request: Request, ctx, s: Session):
 _humans_only(request);return [ep_view(e) for e in s.scalars(select(WebhookEndpoint).where(WebhookEndpoint.company_id==ctx[1]).order_by(WebhookEndpoint.id))]

def create_webhook(x: WebhookIn, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write')
 e=WebhookEndpoint(company_id=cid,url=_url(x.url),secret=wh.new_secret(),events=_events(x.events),created_by=u.id);s.add(e);s.flush();audit(s,cid,u.id,'create','webhook',e.id,{'url':e.url,'events':e.events});s.commit()
 return ep_view(e,secret=True)

def patch_webhook(eid: int, x: WebhookPatch, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write');e=_ep(s,ctx,eid)
 if x.url is not None: e.url=_url(x.url)
 if x.events is not None: e.events=_events(x.events)
 if x.active is not None:
  e.active=x.active
  if x.active: e.consecutive_failures=0
 audit(s,cid,u.id,'update','webhook',e.id,x.model_dump(exclude_none=True));s.commit();return ep_view(e)

def rotate_secret(eid: int, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write');e=_ep(s,ctx,eid);e.secret=wh.new_secret();audit(s,cid,u.id,'rotate_secret','webhook',e.id);s.commit();return ep_view(e,secret=True)

def delete_webhook(eid: int, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write');e=_ep(s,ctx,eid)
 s.execute(delete(WebhookDelivery).where(WebhookDelivery.endpoint_id==e.id));s.delete(e);audit(s,cid,u.id,'delete','webhook',eid,{'url':e.url});s.commit();return {'ok':True}

def test_webhook(eid: int, request: Request, ctx, s: Session):
 """ارسال هم‌زمان یک رویداد آزمایشی و برگرداندن نتیجه (بدون تلاش مجدد خودکار)"""
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write');e=_ep(s,ctx,eid)
 eid2=secrets.token_hex(16);d=WebhookDelivery(company_id=cid,endpoint_id=e.id,event='webhook.test',event_id=eid2,payload={'id':eid2,'event':'webhook.test','created_at':utcnow().isoformat()+'Z','data':{'message':'اتصال آزمایشی'}},status='sending',attempts=MAX_TEST_ATTEMPT)
 s.add(d);s.flush();st=wh.deliver_one(s,d,e);return {'status':st,'response_code':d.response_code,'error':d.error,'delivery_id':d.id}

def deliveries(eid: int, response: Response, request: Request, status: Optional[str], limit: int, offset: int, ctx, s: Session):
 _humans_only(request);e=_ep(s,ctx,eid);q=select(WebhookDelivery).where(WebhookDelivery.endpoint_id==e.id)
 if status: q=q.where(WebhookDelivery.status==status)
 rows=page_rows(s,q.order_by(WebhookDelivery.id.desc()),response,limit,offset)
 return [{'id':d.id,'event':d.event,'event_id':d.event_id,'status':d.status,'attempts':d.attempts,'next_try_at':d.next_try_at,'response_code':d.response_code,'error':d.error,'created_at':d.created_at} for d in rows]

def redeliver(did: int, request: Request, ctx, s: Session):
 _humans_only(request);u,cid,r=ctx;need(ctx,'admin.write');d=same_company(s,WebhookDelivery,did,cid)
 if d.status not in ('failed','delivered'): raise HTTPException(409,'این ارسال هنوز در جریان است')
 d.status='pending';d.attempts=0;d.next_try_at=utcnow();d.error='';audit(s,cid,u.id,'redeliver','webhook',d.endpoint_id,{'delivery_id':d.id});s.commit();return {'id':d.id,'status':d.status}
