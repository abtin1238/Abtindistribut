from __future__ import annotations
import uuid
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import utcnow
from app.models import SyncEvent, Visit
from datetime import datetime, timedelta, timezone
from app.core.security import has_perm, required_perm
from app.modules.automation import add_activity, add_lead, add_task, patch_task
from app.modules.delivery import collect, update_delivery
from app.modules.field import finish_visit, start_visit
from app.modules.finance import payment
from app.modules.gps import ingest_points
from app.modules.sales import create_order
from app.schemas import GpsBatchIn, CollectIn, DeliveryUpdate, LeadActivityIn, LeadIn, OrderIn, PaymentIn, TaskIn, TaskPatch, VisitFinishIn, VisitIn

def _client_time(v):
 try:
  d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
  d=d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d
  return d if d<=utcnow()+timedelta(minutes=5) else None
 except Exception: return None

def _ref_id(s,cid,e):
 if e.get('entity_id') is not None: return int(e['entity_id'])
 r=s.scalar(select(SyncEvent.result_id).where(SyncEvent.company_id==cid,SyncEvent.client_event_id==str(e.get('ref')),SyncEvent.status=='applied')) if e.get('ref') else None
 if not r: raise HTTPException(409,'رکورد مرجع هنوز همگام نشده است')
 return r

SYNC_PERM={'delivery.loaded':('PATCH','/api/deliveries/0'),'delivery.collect':('POST','/api/deliveries/0/collect'),'delivery.start':('PATCH','/api/deliveries/0'),'delivery.delivered':('PATCH','/api/deliveries/0'),'delivery.failed':('PATCH','/api/deliveries/0'),'visit.start':('POST','/api/visits'),'visit.finish':('POST','/api/visits/0/finish'),'order.create':('POST','/api/orders'),'payment.create':('POST','/api/payments'),'lead.create':('POST','/api/leads'),'lead.activity':('POST','/api/leads/0/activities'),'task.create':('POST','/api/tasks'),'task.done':('PATCH','/api/tasks/0'),'gps.points':('POST','/api/gps/points')}

def apply_sync_event(e,ctx,s):
 ty=e.get('type');pl=e.get('payload') or {}
 if ty not in SYNC_PERM: raise HTTPException(400,'نوع رویداد پشتیبانی نمی‌شود')
 need_p=required_perm(*SYNC_PERM[ty])
 if need_p and not has_perm(ctx[2],need_p): raise HTTPException(403,'دسترسی کافی نیست')
 if ty=='delivery.loaded': return update_delivery(_ref_id(s,ctx[1],e),DeliveryUpdate(status='loaded'),ctx,s)['id']
 if ty=='delivery.collect': return collect(_ref_id(s,ctx[1],e),CollectIn(**pl),ctx,s)['record']['id']
 if ty=='delivery.start': return update_delivery(_ref_id(s,ctx[1],e),DeliveryUpdate(status='out_for_delivery'),ctx,s)['id']
 if ty=='delivery.delivered': return update_delivery(_ref_id(s,ctx[1],e),DeliveryUpdate(**{**pl,'status':'delivered'}),ctx,s)['id']
 if ty=='delivery.failed': return update_delivery(_ref_id(s,ctx[1],e),DeliveryUpdate(**{**pl,'status':'failed'}),ctx,s)['id']
 if ty=='visit.start':
  v=start_visit(VisitIn(**{k:pl.get(k) for k in ('customer_id','plan_id','lat','lng','note') if pl.get(k) is not None}),ctx,s);ct=_client_time(pl.get('started_at'))
  if ct: row=s.get(Visit,v['id']);row.started_at=ct;s.commit()
  return v['id']
 if ty=='visit.finish':
  vid=_ref_id(s,ctx[1],e);fk=('result','no_order_reason','note','order_id');r=finish_visit(vid,ctx,s,VisitFinishIn(**{k:pl[k] for k in fk if pl.get(k) is not None}) if any(pl.get(k) is not None for k in fk) else None);ct=_client_time(pl.get('ended_at'))
  if ct: row=s.get(Visit,vid);row.ended_at=ct;s.commit()
  return r['id']
 if ty=='order.create': return create_order(OrderIn(**pl),ctx,s)['id']
 if ty=='payment.create': return payment(PaymentIn(**pl),ctx,s)['id']
 if ty=='lead.create': return add_lead(LeadIn(**pl),ctx,s)['id']
 if ty=='lead.activity': return add_activity(_ref_id(s,ctx[1],e),LeadActivityIn(**pl),ctx,s)['id']
 if ty=='task.create': return add_task(TaskIn(**pl),ctx,s)['id']
 if ty=='task.done': return patch_task(_ref_id(s,ctx[1],e),TaskPatch(status='done'),ctx,s)['id']
 if ty=='gps.points': ingest_points(GpsBatchIn(**pl),ctx,s);return None

def sync(payload: dict, ctx, s: Session):
 u,cid,r=ctx;events=payload.get('events',[])
 if not isinstance(events,list) or len(events)>200: raise HTTPException(400,'حداکثر ۲۰۰ رویداد در هر درخواست')
 applied=0;results=[]
 for e in events:
  if not isinstance(e,dict): results.append({'id':None,'status':'rejected','detail':'ساختار رویداد نامعتبر'});continue
  eid=str(e.get('id') or uuid.uuid4());prev=s.scalar(select(SyncEvent).where(SyncEvent.company_id==cid,SyncEvent.client_event_id==eid))
  if prev: results.append({'id':eid,'status':'duplicate','previous':prev.status,'result_id':prev.result_id});continue
  status,err,rid='applied','',None;conflict=False
  try:
   rid=apply_sync_event(e,ctx,s)
  except HTTPException as ex:
   s.rollback();status='rejected';err=str(ex.detail);conflict=ex.status_code==409
   if conflict and 'همگام' in err: results.append({'id':eid,'status':'retry','detail':err});continue
  except Exception as ex:
   s.rollback()
   if isinstance(ex,ValueError) or ex.__class__.__name__=='ValidationError': status='rejected';err='داده‌ی رویداد نامعتبر است'
   else: results.append({'id':eid,'status':'retry','detail':'خطای موقت سرور'});continue
  s.add(SyncEvent(company_id=cid,user_id=u.id,client_event_id=eid,event_type=str(e.get('type','unknown'))[:80],payload=jsonable_encoder(e),status=status,error=err,result_id=rid));s.commit()
  if status=='applied': applied+=1
  results.append({'id':eid,'status':status,'detail':err,'result_id':rid,**({'code':'conflict'} if conflict else {})})
 return {'accepted':applied,'results':results,'server_time':utcnow().isoformat()}

def my_events(status: str | None, limit: int, ctx, s: Session):
 """تاریخچه‌ی رویدادهای همگام‌شده‌ی خودِ کاربر (برای نمایش ردشده/تعارض به کلاینت آفلاین)"""
 u,cid,r=ctx;q=select(SyncEvent).where(SyncEvent.company_id==cid,SyncEvent.user_id==u.id)
 if status: q=q.where(SyncEvent.status==status)
 return [{'id':x.client_event_id,'type':x.event_type,'status':x.status,'detail':x.error,'result_id':x.result_id,'at':x.created_at} for x in s.scalars(q.order_by(SyncEvent.id.desc()).limit(max(1,min(limit,500))))]
