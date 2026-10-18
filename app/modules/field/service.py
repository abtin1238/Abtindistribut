from __future__ import annotations
from datetime import date
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import audit, obj
from app.core.config import utcnow
from app.core.uploads import store_image
from app.core.security import has_all, need
from app.models import Customer, Membership, Order, Setting, Visit, VisitPlan, VisitPlanItem
from app.services.geo import gps_check, suggest_route, DEFAULT_RADIUS_M
from .schemas import VisitIn, PlanIn, VisitFinishIn, VisitRadiusIn

VISIT_RESULTS=('ordered','follow_up','no_order','not_available','closed')

def visit_radius(s,cid)->float:
 v=s.scalar(select(Setting.value).where(Setting.company_id==cid,Setting.key=='visit_radius_m'))
 try: return float(v) if v not in (None,'') else DEFAULT_RADIUS_M
 except ValueError: return DEFAULT_RADIUS_M

def _cust_names(s,cid,ids): return {c.id:c.name for c in s.scalars(select(Customer).where(Customer.company_id==cid,Customer.id.in_(list(ids))))} if ids else {}

def _plan_rows(s,cid,plan_ids):
 rows=s.execute(select(VisitPlanItem,Customer,VisitPlan).join(Customer,Customer.id==VisitPlanItem.customer_id).join(VisitPlan,VisitPlan.id==VisitPlanItem.plan_id).where(VisitPlanItem.plan_id.in_(plan_ids),Customer.company_id==cid).order_by(VisitPlanItem.plan_id,VisitPlanItem.sequence)).all()
 return [{'plan_id':i.plan_id,'item_id':i.id,'sequence':i.sequence,'status':i.status,'customer':{'id':c.id,'code':c.code,'name':c.name,'phone':c.phone,'address':c.address,'region':c.region,'lat':c.lat,'lng':c.lng}} for i,c,p in rows]

def get_visit_settings(ctx, s: Session):
 return {'radius_m': visit_radius(s, ctx[1])}

def put_visit_settings(x: VisitRadiusIn, ctx, s: Session):
 u,cid,r=ctx;need(ctx,'settings.write');row=s.scalar(select(Setting).where(Setting.company_id==cid,Setting.key=='visit_radius_m'))
 if row: row.value=str(x.radius_m)
 else: s.add(Setting(company_id=cid,key='visit_radius_m',value=str(x.radius_m)))
 audit(s,cid,u.id,'update','visit_radius',None,x.model_dump());s.commit();return {'radius_m':x.radius_m}

def start_visit(x: VisitIn, ctx, s: Session):
 u,cid,r=ctx;c=s.get(Customer,x.customer_id)
 if not c or c.company_id!=cid:raise HTTPException(404,'مشتری یافت نشد')
 pl=None
 if x.plan_id:
  pl=s.get(VisitPlan,x.plan_id)
  if not pl or pl.company_id!=cid or (pl.user_id!=u.id and not has_all(r)):raise HTTPException(404,'برنامه یافت نشد')
 dist,st=gps_check(x.lat,x.lng,c.lat,c.lng,visit_radius(s,cid))
 v=Visit(company_id=cid,user_id=u.id,distance_m=dist,gps_status=st,**x.model_dump());s.add(v)
 if pl:
  pi=s.scalar(select(VisitPlanItem).where(VisitPlanItem.plan_id==pl.id,VisitPlanItem.customer_id==x.customer_id))
  if pi:
   pi.status='visited';s.flush()
   if not s.scalar(select(func.count()).select_from(VisitPlanItem).where(VisitPlanItem.plan_id==pl.id,VisitPlanItem.status!='visited')): pl.status='done'
 audit(s,cid,u.id,'start','visit',None,{**x.model_dump(),'gps_status':st,'distance_m':dist});s.commit();s.refresh(v);return obj(v)

def finish_visit(vid: int, ctx, s: Session, x: Optional[VisitFinishIn]=None):
 u,cid,r=ctx;v=s.get(Visit,vid,with_for_update=True)
 if not v or v.company_id!=cid:raise HTTPException(404,'ویزیت یافت نشد')
 if v.user_id!=u.id and not has_all(r):raise HTTPException(403,'ویزیت متعلق به شما نیست')
 if x is not None:
  if x.result and x.result not in VISIT_RESULTS:raise HTTPException(400,'نتیجه‌ی ویزیت نامعتبر است')
  if x.result=='no_order' and not x.no_order_reason.strip():raise HTTPException(400,'دلیل عدم سفارش الزامی است')
  if x.order_id is not None:
   o=s.get(Order,x.order_id)
   if not o or o.company_id!=cid or o.customer_id!=v.customer_id or (o.seller_id!=v.user_id and not has_all(r)):raise HTTPException(404,'سفارش یافت نشد')
   v.order_id=o.id
  if v.ended_at and (x.result or x.note is not None):raise HTTPException(409,'این ویزیت قبلاً بسته شده است')
  v.result=x.result or v.result;v.no_order_reason=x.no_order_reason.strip() if x.result=='no_order' else ''
  if x.note is not None: v.note=x.note
  if x.result=='ordered' and not v.order_id:
   o=s.scalar(select(Order).where(Order.company_id==cid,Order.customer_id==v.customer_id,Order.seller_id==v.user_id,Order.created_at>=v.started_at).order_by(Order.id.desc()))
   if o: v.order_id=o.id
 if not v.ended_at: v.ended_at=utcnow()
 audit(s,cid,u.id,'finish','visit',v.id,{'result':v.result,'order_id':v.order_id});s.commit();return obj(v)

async def visit_photo(vid: int, file: UploadFile, ctx, s: Session):
 from app.modules.platform import MAX_UPLOAD
 u,cid,r=ctx;v=s.get(Visit,vid)
 if not v or v.company_id!=cid:raise HTTPException(404,'ویزیت یافت نشد')
 if v.user_id!=u.id and not has_all(r):raise HTTPException(404,'ویزیت یافت نشد')
 doc,size=store_image(s,cid,'visit',v.id,await file.read(MAX_UPLOAD+1),MAX_UPLOAD);v.photo=f'/api/documents/{doc.id}/download'
 audit(s,cid,u.id,'photo','visit',v.id,{'document_id':doc.id,'size':size});s.commit();return {'id':v.id,'photo':v.photo,'document_id':doc.id}

def today_visits(day: Optional[date], ctx, s: Session):
 u,cid,r=ctx;q=select(Visit).where(Visit.company_id==cid,func.date(Visit.started_at)==(day or date.today()))
 if not has_all(r):q=q.where(Visit.user_id==u.id)
 rows=s.scalars(q.order_by(Visit.id)).all();names=_cust_names(s,cid,{v.customer_id for v in rows})
 return [{**obj(x),'customer_name':names.get(x.customer_id,'')} for x in rows]

def list_visits(start: Optional[date], end: Optional[date], user_id: Optional[int], customer_id: Optional[int], gps_status: Optional[str], limit: int, ctx, s: Session):
 u,cid,r=ctx;q=select(Visit).where(Visit.company_id==cid)
 if not has_all(r):q=q.where(Visit.user_id==u.id)
 elif user_id:q=q.where(Visit.user_id==user_id)
 if start:q=q.where(func.date(Visit.started_at)>=start)
 if end:q=q.where(func.date(Visit.started_at)<=end)
 if customer_id:q=q.where(Visit.customer_id==customer_id)
 if gps_status:q=q.where(Visit.gps_status==gps_status)
 rows=s.scalars(q.order_by(Visit.id.desc()).limit(limit)).all();names=_cust_names(s,cid,{v.customer_id for v in rows})
 return [{**obj(x),'customer_name':names.get(x.customer_id,'')} for x in rows]

def visit_plans(ctx, s: Session):
 u,cid,r=ctx;q=select(VisitPlan).where(VisitPlan.company_id==cid);q=q if has_all(r) else q.where(VisitPlan.user_id==u.id)
 return [obj(x) for x in s.scalars(q.order_by(VisitPlan.id.desc()).limit(500))]

def create_plan(x: PlanIn, ctx, s: Session):
 u,cid,r=ctx
 if x.user_id!=u.id and not has_all(r):raise HTTPException(403,'ساخت برنامه برای دیگران مجاز نیست')
 if not s.scalar(select(Membership).where(Membership.user_id==x.user_id,Membership.company_id==cid)):raise HTTPException(400,'کاربر متعلق به شرکت نیست')
 if len(set(x.customer_ids))!=len(x.customer_ids):raise HTTPException(400,'مشتری تکراری در برنامه')
 p=VisitPlan(company_id=cid,user_id=x.user_id,day=x.day);s.add(p);s.flush()
 for i,cid2 in enumerate(x.customer_ids,1):
  if not s.scalar(select(Customer).where(Customer.id==cid2,Customer.company_id==cid)):raise HTTPException(400,'مشتری نامعتبر در برنامه')
  s.add(VisitPlanItem(plan_id=p.id,customer_id=cid2,sequence=i))
 s.commit();s.refresh(p);return obj(p)

def today_plan(day: Optional[date], ctx, s: Session):
 u,cid,r=ctx;ids=list(s.scalars(select(VisitPlan.id).where(VisitPlan.company_id==cid,VisitPlan.user_id==u.id,VisitPlan.day==(day or date.today()))))
 return _plan_rows(s,cid,ids) if ids else []

def suggest_plan(region: str, day: Optional[date], lat: Optional[float], lng: Optional[float], limit: int, ctx, s: Session):
 u,cid,r=ctx;q=select(Customer).where(Customer.company_id==cid,Customer.active==True)
 if region.strip():q=q.where(Customer.region==region.strip())
 custs=s.scalars(q).all();ids=[c.id for c in custs]
 last={cid_:d for cid_,d in s.execute(select(Visit.customer_id,func.max(Visit.started_at)).where(Visit.company_id==cid,Visit.customer_id.in_(ids)).group_by(Visit.customer_id))} if ids else {}
 today=day or date.today()
 cands=[{'id':c.id,'code':c.code,'name':c.name,'region':c.region,'lat':c.lat,'lng':c.lng,'last_visit':(last[c.id].date() if last.get(c.id) else None)} for c in custs if not (last.get(c.id) and last[c.id].date()==today)]
 res=suggest_route(cands,limit,(lat,lng) if lat is not None and lng is not None else None)
 return [{**x,'last_visit':x['last_visit'].isoformat() if x['last_visit'] else None} for x in res]

def plan_items(pid: int, ctx, s: Session):
 p=s.get(VisitPlan,pid)
 if not p or p.company_id!=ctx[1] or (not has_all(ctx[2]) and p.user_id!=ctx[0].id):raise HTTPException(404,'برنامه یافت نشد')
 return [obj(x) for x in s.scalars(select(VisitPlanItem).where(VisitPlanItem.plan_id==pid).order_by(VisitPlanItem.sequence)).all()]
