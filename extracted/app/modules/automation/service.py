from __future__ import annotations
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from typing import Optional
from app.core.common import D, Q2, audit, num, obj
from app.core.config import utcnow
from app.core.security import has_all, has_perm
from app.services.notify import notify
from app.models import Customer, Lead, LeadActivity, Membership, Product, Proposal, ProposalLine, Target, Task, Visit, Invoice, Order, User
from app.modules.sales import create_order
from app.schemas import ItemIn, OrderIn
from app.services.accounting import effective_price
from .schemas import LeadIn, LeadStageIn, LeadActivityIn, TaskIn, TaskPatch, ProposalIn, ProposalAcceptIn, TargetIn

OPEN_STAGES=('new','contacted','qualified','proposal','negotiation')

STAGES=OPEN_STAGES+('won','lost')

WIN_FROM=('qualified','proposal','negotiation')

ACT_KINDS=('call','visit','meeting','note')

TASK_KINDS=('task','call')

def _lead(s,ctx,lid,lock=False):
 u,cid,r=ctx;x=s.get(Lead,lid,with_for_update=lock)
 if not x or x.company_id!=cid or (not has_all(r) and x.owner_id!=u.id): raise HTTPException(404,'سرنخ یافت نشد')
 return x

def _log(s,cid,uid,lid,kind,note='',frm='',to=''): s.add(LeadActivity(company_id=cid,lead_id=lid,user_id=uid,kind=kind,note=note,from_stage=frm,to_stage=to))

def move_stage(s,cid,uid,lead,to,lost_reason='',note='',force_win=False):
 if to not in STAGES: raise HTTPException(400,'مرحله‌ی نامعتبر')
 if lead.stage in ('won','lost'): raise HTTPException(409,'سرنخ بسته شده است')
 if to==lead.stage: return lead
 if to=='lost' and not lost_reason.strip(): raise HTTPException(400,'دلیل ازدست‌رفتن الزامی است')
 if to=='won' and lead.stage not in WIN_FROM and not force_win: raise HTTPException(409,'سرنخ باید ابتدا به مرحله‌ی «واجد شرایط» یا بالاتر برسد')
 frm=lead.stage;lead.stage=to
 if to in ('won','lost'): lead.closed_at=utcnow();lead.lost_reason=lost_reason.strip() if to=='lost' else ''
 _log(s,cid,uid,lead.id,'stage',note,frm,to);return lead

# ---------- وظیفه و یادآوری ----------
def _task(s,ctx,tid,lock=False):
 u,cid,r=ctx;t=s.get(Task,tid,with_for_update=lock)
 if not t or t.company_id!=cid or (not has_all(r) and u.id not in (t.assignee_id,t.created_by)): raise HTTPException(404,'وظیفه یافت نشد')
 return t

# ---------- پیشنهاد فروش ----------
def _prop(s,ctx,pid,lock=False):
 u,cid,r=ctx;p=s.get(Proposal,pid,with_for_update=lock)
 if not p or p.company_id!=cid or (not has_all(r) and p.owner_id!=u.id): raise HTTPException(404,'پیشنهاد یافت نشد')
 return p

def _prop_json(s,p): return {**obj(p),'lines':[obj(l) for l in s.scalars(select(ProposalLine).where(ProposalLine.proposal_id==p.id).order_by(ProposalLine.id))]}

# ---------- تارگت و پورسانت ----------
def _month_range(period):
 y,m=int(period[:4]),int(period[5:7]);a=datetime(y,m,1);return a,(datetime(y+1,1,1) if m==12 else datetime(y,m+1,1))

def _period(v):
 v=v or utcnow().strftime('%Y-%m')
 try: _month_range(v);assert len(v)==7 and v[4]=='-'
 except Exception: raise HTTPException(400,'دوره باید به شکل YYYY-MM باشد')
 return v

def performance(s,cid,period,user_ids=None):
 a,b=_month_range(period);tq=select(Target).where(Target.company_id==cid,Target.period==period)
 if user_ids is not None: tq=tq.where(Target.user_id.in_(user_ids))
 out=[]
 for t in s.scalars(tq.order_by(Target.user_id)):
  # فروش خالص = مجموع (جمع فاکتور − برگشتی) فاکتورهای غیرباطل همان ماه که سفارشش را این کاربر ثبت کرده است
  actual=D(s.scalar(select(func.coalesce(func.sum(Invoice.total-Invoice.returned),0)).join(Order,Order.id==Invoice.order_id).where(Invoice.company_id==cid,Invoice.status!='cancelled',Order.seller_id==t.user_id,Invoice.issued_at>=a,Invoice.issued_at<b)))
  orders=s.scalar(select(func.count()).select_from(Order).where(Order.company_id==cid,Order.seller_id==t.user_id,Order.status!='cancelled',Order.created_at>=a,Order.created_at<b))
  visits=s.scalar(select(func.count()).select_from(Visit).where(Visit.company_id==cid,Visit.user_id==t.user_id,Visit.started_at>=a,Visit.started_at<b))
  tgt=D(t.sales_target);u=s.get(User,t.user_id)
  out.append({'user_id':t.user_id,'user_name':u.name if u else '','period':period,'sales_target':tgt,'actual':actual,'attainment_percent':(actual*100/tgt).quantize(Q2) if tgt>0 else None,'commission_percent':D(t.commission_percent),'commission':(max(actual,Decimal(0))*D(t.commission_percent)/100).quantize(Q2),'orders':orders,'visits':visits})
 return out

# ---------- یادآوری خودکار ----------
def run_reminders(s,cid=None,today=None):
 """برای وظیفه/تماس و پیگیری سرنخِ سررسیدشده یک‌بار اعلان می‌سازد (idempotent: `Task.reminded`، `Lead.reminded_on`)."""
 today=today or date.today();n=0
 tq=select(Task).where(Task.status=='open',Task.reminded==False,Task.due_date!=None,Task.due_date<=today)
 lq=select(Lead).where(Lead.stage.in_(OPEN_STAGES),Lead.next_followup!=None,Lead.next_followup<=today,or_(Lead.reminded_on==None,Lead.reminded_on<Lead.next_followup))
 if cid: tq=tq.where(Task.company_id==cid);lq=lq.where(Lead.company_id==cid)
 for t in s.scalars(tq.with_for_update()).all():
  notify(s,t.company_id,[t.assignee_id],'task_reminder','یادآوری تماس' if t.kind=='call' else 'یادآوری وظیفه',t.title,'task',t.id);t.reminded=True;n+=1
 for l in s.scalars(lq.with_for_update()).all():
  notify(s,l.company_id,[l.owner_id],'lead_followup','پیگیری سرنخ',l.title,'lead',l.id);l.reminded_on=today;n+=1
 s.commit();return n

def leads(stage: Optional[str], q: str, owner_id: Optional[int], limit: int, ctx, s: Session):
 u,cid,r=ctx;sel=select(Lead).where(Lead.company_id==cid)
 if not has_all(r): sel=sel.where(Lead.owner_id==u.id)
 elif owner_id: sel=sel.where(Lead.owner_id==owner_id)
 if stage: sel=sel.where(Lead.stage==stage)
 if q.strip(): sel=sel.where(Lead.title.ilike('%'+q.strip().replace('%','').replace('_','')+'%'))
 return [obj(x) for x in s.scalars(sel.order_by(Lead.id.desc()).limit(limit))]

def add_lead(x: LeadIn, ctx, s: Session):
 u,cid,r=ctx
 if x.stage not in OPEN_STAGES: raise HTTPException(400,'سرنخ جدید فقط در مرحله‌های باز ساخته می‌شود')
 if x.customer_id and not s.scalar(select(Customer.id).where(Customer.id==x.customer_id,Customer.company_id==cid)): raise HTTPException(404,'مشتری یافت نشد')
 q=Lead(company_id=cid,owner_id=u.id,**x.model_dump());s.add(q);s.flush();_log(s,cid,u.id,q.id,'stage','',  '',q.stage);audit(s,cid,u.id,'create','lead',q.id);s.commit();s.refresh(q);return obj(q)

def lead_followups(days: int, ctx, s: Session):
 u,cid,r=ctx;today=date.today();sel=select(Lead).where(Lead.company_id==cid,Lead.stage.in_(OPEN_STAGES),Lead.next_followup!=None,Lead.next_followup<=today+timedelta(days=days))
 if not has_all(r): sel=sel.where(Lead.owner_id==u.id)
 return [{**obj(x),'overdue':x.next_followup<today} for x in s.scalars(sel.order_by(Lead.next_followup,Lead.id).limit(500))]

def lead_stage(lid: int, x: LeadStageIn, ctx, s: Session):
 u,cid,r=ctx;lead=_lead(s,ctx,lid,True);move_stage(s,cid,u.id,lead,x.stage,x.lost_reason,x.note);audit(s,cid,u.id,'stage','lead',lead.id,x.model_dump());s.commit();return obj(lead)

def add_activity(lid: int, x: LeadActivityIn, ctx, s: Session):
 u,cid,r=ctx;lead=_lead(s,ctx,lid,True)
 if x.kind not in ACT_KINDS: raise HTTPException(400,'نوع فعالیت نامعتبر')
 if x.next_followup and x.next_followup<date.today(): raise HTTPException(400,'تاریخ پیگیری در گذشته است')
 _log(s,cid,u.id,lead.id,x.kind,x.note)
 if x.next_followup: lead.next_followup=x.next_followup
 if lead.stage=='new' and x.kind in ('call','visit','meeting'): _log(s,cid,u.id,lead.id,'stage','','new','contacted');lead.stage='contacted'
 s.commit();return obj(lead)

def lead_activities(lid: int, ctx, s: Session):
 _lead(s,ctx,lid);return [obj(a) for a in s.scalars(select(LeadActivity).where(LeadActivity.lead_id==lid).order_by(LeadActivity.id.desc()).limit(200))]

def tasks(status: Optional[str], assignee_id: Optional[int], ctx, s: Session):
 u,cid,r=ctx;q=select(Task).where(Task.company_id==cid)
 if not has_all(r): q=q.where((Task.assignee_id==u.id)|(Task.created_by==u.id))
 elif assignee_id: q=q.where(Task.assignee_id==assignee_id)
 if status: q=q.where(Task.status==status)
 return [obj(t) for t in s.scalars(q.order_by(Task.due_date.is_(None),Task.due_date,Task.id).limit(500))]

def add_task(x: TaskIn, ctx, s: Session):
 u,cid,r=ctx;aid=x.assignee_id or u.id
 if x.kind not in TASK_KINDS: raise HTTPException(400,'نوع وظیفه نامعتبر')
 if aid!=u.id:
  if not has_all(r): raise HTTPException(403,'واگذاری وظیفه به دیگران مجاز نیست')
  if not s.scalar(select(Membership.id).where(Membership.user_id==aid,Membership.company_id==cid)): raise HTTPException(400,'کاربر متعلق به شرکت نیست')
 if x.lead_id: _lead(s,ctx,x.lead_id)
 if x.customer_id and not s.scalar(select(Customer.id).where(Customer.id==x.customer_id,Customer.company_id==cid)): raise HTTPException(404,'مشتری یافت نشد')
 t=Task(company_id=cid,assignee_id=aid,created_by=u.id,**x.model_dump(exclude={'assignee_id'}));s.add(t)
 if aid!=u.id: notify(s,cid,[aid],'task_assigned','وظیفه‌ی جدید',x.title,'task')
 s.flush();audit(s,cid,u.id,'create','task',t.id);s.commit();s.refresh(t);return obj(t)

def patch_task(tid: int, x: TaskPatch, ctx, s: Session):
 u,cid,r=ctx;t=_task(s,ctx,tid,True)
 if x.status not in ('done','cancelled'): raise HTTPException(400,'وضعیت نامعتبر')
 if t.status!='open': raise HTTPException(409,'وظیفه قبلاً بسته شده است')
 t.status=x.status;t.done_at=utcnow() if x.status=='done' else None;audit(s,cid,u.id,x.status,'task',t.id);s.commit();return obj(t)

def reminders(days: int, ctx, s: Session):
 u,cid,r=ctx;today=date.today();lim=today+timedelta(days=days)
 ts=s.scalars(select(Task).where(Task.company_id==cid,Task.assignee_id==u.id,Task.status=='open',Task.due_date!=None,Task.due_date<=lim).order_by(Task.due_date,Task.id).limit(200)).all()
 ls=s.scalars(select(Lead).where(Lead.company_id==cid,Lead.owner_id==u.id,Lead.stage.in_(OPEN_STAGES),Lead.next_followup!=None,Lead.next_followup<=lim).order_by(Lead.next_followup,Lead.id).limit(200)).all()
 f=lambda x,d:{**obj(x),'overdue':d<today}
 return {'calls':[f(t,t.due_date) for t in ts if t.kind=='call'],'tasks':[f(t,t.due_date) for t in ts if t.kind!='call'],'lead_followups':[f(l,l.next_followup) for l in ls]}

def add_proposal(x: ProposalIn, ctx, s: Session):
 u,cid,r=ctx;c=s.get(Customer,x.customer_id)
 if not c or c.company_id!=cid: raise HTTPException(404,'مشتری یافت نشد')
 if x.valid_until and x.valid_until<date.today(): raise HTTPException(400,'تاریخ اعتبار در گذشته است')
 lead=None
 if x.lead_id:
  lead=_lead(s,ctx,x.lead_id)
  if lead.customer_id and lead.customer_id!=c.id: raise HTTPException(400,'سرنخ به مشتری دیگری مربوط است')
 lines=[];total=Decimal(0)
 for it in x.items:
  p=s.get(Product,it.product_id)
  if not p or p.company_id!=cid: raise HTTPException(404,'کالا یافت نشد')
  price=effective_price(s,cid,p.id,c.customer_group,it.quantity);lt=(it.quantity*price).quantize(Q2);total+=lt;lines.append((p.id,it.quantity,price,lt))
 pr=Proposal(company_id=cid,number=num('PR',Proposal,s),customer_id=c.id,lead_id=x.lead_id,owner_id=u.id,valid_until=x.valid_until,total=total,notes=x.notes);s.add(pr);s.flush()
 for pid,q,price,lt in lines: s.add(ProposalLine(proposal_id=pr.id,product_id=pid,quantity=q,unit_price=price,line_total=lt))
 audit(s,cid,u.id,'create','proposal',pr.id,{'number':pr.number});s.commit();return _prop_json(s,pr)

def proposals(status: Optional[str], ctx, s: Session):
 u,cid,r=ctx;q=select(Proposal).where(Proposal.company_id==cid)
 if not has_all(r): q=q.where(Proposal.owner_id==u.id)
 if status: q=q.where(Proposal.status==status)
 return [obj(p) for p in s.scalars(q.order_by(Proposal.id.desc()).limit(500))]

def proposal(pid: int, ctx, s: Session):
 return _prop_json(s, _prop(s, ctx, pid))

def send_proposal(pid: int, ctx, s: Session):
 u,cid,r=ctx;p=_prop(s,ctx,pid,True)
 if p.status!='draft': raise HTTPException(409,'فقط پیش‌نویس قابل ارسال است')
 p.status='sent'
 if p.lead_id:
  l=s.get(Lead,p.lead_id,with_for_update=True)
  if l and l.stage in ('new','contacted','qualified'): move_stage(s,cid,u.id,l,'proposal','پیشنهاد '+p.number)
 audit(s,cid,u.id,'send','proposal',p.id);s.commit();return obj(p)

def reject_proposal(pid: int, ctx, s: Session):
 u,cid,r=ctx;p=_prop(s,ctx,pid,True)
 if p.status not in ('draft','sent'): raise HTTPException(409,'وضعیت پیشنهاد اجازه‌ی رد نمی‌دهد')
 p.status='rejected';audit(s,cid,u.id,'reject','proposal',p.id);s.commit();return obj(p)

def accept_proposal(pid: int, x: ProposalAcceptIn, ctx, s: Session):
 u,cid,r=ctx
 if not has_perm(r,'sales.write'): raise HTTPException(403,'دسترسی کافی نیست')
 p=_prop(s,ctx,pid,True)
 if p.status!='sent': raise HTTPException(409,'فقط پیشنهاد ارسال‌شده قابل پذیرش است')
 if p.valid_until and p.valid_until<date.today(): raise HTTPException(409,'مهلت اعتبار پیشنهاد گذشته است')
 items=[ItemIn(product_id=l.product_id,quantity=l.quantity) for l in s.scalars(select(ProposalLine).where(ProposalLine.proposal_id==p.id))]
 o=create_order(OrderIn(customer_id=p.customer_id,warehouse_id=x.warehouse_id,items=items),ctx,s)  # قیمت و اعتبار و موجودی دوباره سمت سرور بررسی می‌شود
 p.status='accepted';p.order_id=o['id']
 if p.lead_id:
  l=s.get(Lead,p.lead_id,with_for_update=True)
  if l and l.stage not in ('won','lost'): move_stage(s,cid,u.id,l,'won','سفارش '+o['number'],force_win=True)
 audit(s,cid,u.id,'accept','proposal',p.id,{'order_id':o['id']});s.commit();return {**obj(p),'order':o}

def set_target(x: TargetIn, ctx, s: Session):
 u,cid,r=ctx
 if not has_all(r): raise HTTPException(403,'فقط مدیر می‌تواند تارگت تعیین کند')
 if not s.scalar(select(Membership.id).where(Membership.user_id==x.user_id,Membership.company_id==cid)): raise HTTPException(400,'کاربر متعلق به شرکت نیست')
 t=s.scalar(select(Target).where(Target.company_id==cid,Target.user_id==x.user_id,Target.period==x.period))
 if t: t.sales_target=x.sales_target;t.commission_percent=x.commission_percent
 else: t=Target(company_id=cid,**x.model_dump());s.add(t)
 audit(s,cid,u.id,'set','target',None,x.model_dump());s.commit();s.refresh(t);return obj(t)

def targets(period: Optional[str], ctx, s: Session):
 u,cid,r=ctx;q=select(Target).where(Target.company_id==cid,Target.period==_period(period))
 if not has_all(r): q=q.where(Target.user_id==u.id)
 return [obj(t) for t in s.scalars(q)]

def target_performance(period: Optional[str], ctx, s: Session):
 u,cid,r=ctx;return performance(s,cid,_period(period),None if has_all(r) else [u.id])

def funnel(start: Optional[date], end: Optional[date], owner_id: Optional[int], ctx, s: Session):
 u,cid,r=ctx;uid=owner_id if (has_all(r) and owner_id) else (None if has_all(r) else u.id)
 lq=select(Lead).where(Lead.company_id==cid);vq=select(Visit).where(Visit.company_id==cid)
 if uid: lq=lq.where(Lead.owner_id==uid);vq=vq.where(Visit.user_id==uid)
 if start: lq=lq.where(Lead.created_at>=datetime.combine(start,datetime.min.time()));vq=vq.where(Visit.started_at>=datetime.combine(start,datetime.min.time()))
 if end: e=datetime.combine(end+timedelta(days=1),datetime.min.time());lq=lq.where(Lead.created_at<e);vq=vq.where(Visit.started_at<e)
 L=s.scalars(lq).all();V=s.scalars(vq).all()
 stages={st:{'count':0,'value':Decimal(0)} for st in STAGES}
 for l in L: stages[l.stage]['count']+=1;stages[l.stage]['value']+=D(l.value)
 won=[l for l in L if l.stage=='won'];lost=[l for l in L if l.stage=='lost'];reasons={}
 for l in lost: reasons[l.lost_reason or '—']=reasons.get(l.lost_reason or '—',0)+1
 days=[(l.closed_at-l.created_at).total_seconds()/86400 for l in won if l.closed_at and l.created_at]
 closed=len(won)+len(lost);nov={}
 for v in V:
  if v.result=='no_order': nov[v.no_order_reason or '—']=nov.get(v.no_order_reason or '—',0)+1
 done=[v for v in V if v.result]
 return {'leads':{'total':len(L),'stages':stages,'won':len(won),'lost':len(lost),'open':len(L)-closed,'win_rate':round(len(won)/closed,4) if closed else None,'created_to_won':round(len(won)/len(L),4) if L else None,'avg_days_to_win':round(sum(days)/len(days),1) if days else None,'won_value':sum((D(l.value) for l in won),Decimal(0)),'lost_reasons':reasons},
  'visits':{'total':len(V),'with_result':len(done),'ordered':sum(1 for v in V if v.result=='ordered'),'order_rate':round(sum(1 for v in V if v.result=='ordered')/len(done),4) if done else None,'out_of_range':sum(1 for v in V if v.gps_status=='out_of_range'),'no_order_reasons':nov}}

def run_reminders_now(ctx, s: Session):
 u,cid,r=ctx
 if not has_all(r): raise HTTPException(403,'دسترسی کافی نیست')
 return {'notified':run_reminders(s,cid)}
