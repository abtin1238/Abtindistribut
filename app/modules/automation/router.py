from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import db
from app.core.security import current
from app.schemas import LeadActivityIn, LeadIn, LeadStageIn, ProposalAcceptIn, ProposalIn, TargetIn, TaskIn, TaskPatch
from .service import leads as _s_leads, add_lead as _s_add_lead, lead_followups as _s_lead_followups, lead_stage as _s_lead_stage, add_activity as _s_add_activity, lead_activities as _s_lead_activities, tasks as _s_tasks, add_task as _s_add_task, patch_task as _s_patch_task, reminders as _s_reminders, add_proposal as _s_add_proposal, proposals as _s_proposals, proposal as _s_proposal, send_proposal as _s_send_proposal, reject_proposal as _s_reject_proposal, accept_proposal as _s_accept_proposal, set_target as _s_set_target, targets as _s_targets, target_performance as _s_target_performance, funnel as _s_funnel, run_reminders_now as _s_run_reminders_now

router=APIRouter()

@router.get('/api/leads')
def leads(stage: Optional[str]=None, q: str=Query('', max_length=100), owner_id: Optional[int]=None, limit: int=Query(500, ge=1, le=500), ctx=Depends(current), s: Session=Depends(db)):
 return _s_leads(stage=stage, q=q, owner_id=owner_id, limit=limit, ctx=ctx, s=s)

@router.post('/api/leads')
def add_lead(x: LeadIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_lead(x=x, ctx=ctx, s=s)

@router.get('/api/leads/followups')
def lead_followups(days: int=Query(0, ge=0, le=60), ctx=Depends(current), s: Session=Depends(db)):
 return _s_lead_followups(days=days, ctx=ctx, s=s)

@router.patch('/api/leads/{lid}/stage')
def lead_stage(lid: int, x: LeadStageIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_lead_stage(lid=lid, x=x, ctx=ctx, s=s)

@router.post('/api/leads/{lid}/activities')
def add_activity(lid: int, x: LeadActivityIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_activity(lid=lid, x=x, ctx=ctx, s=s)

@router.get('/api/leads/{lid}/activities')
def lead_activities(lid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_lead_activities(lid=lid, ctx=ctx, s=s)

@router.get('/api/tasks')
def tasks(status: Optional[str]=None, assignee_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_tasks(status=status, assignee_id=assignee_id, ctx=ctx, s=s)

@router.post('/api/tasks')
def add_task(x: TaskIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_task(x=x, ctx=ctx, s=s)

@router.patch('/api/tasks/{tid}')
def patch_task(tid: int, x: TaskPatch, ctx=Depends(current), s: Session=Depends(db)):
 return _s_patch_task(tid=tid, x=x, ctx=ctx, s=s)

@router.get('/api/tasks/reminders')
def reminders(days: int=Query(0, ge=0, le=30), ctx=Depends(current), s: Session=Depends(db)):
 return _s_reminders(days=days, ctx=ctx, s=s)

@router.post('/api/proposals')
def add_proposal(x: ProposalIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_add_proposal(x=x, ctx=ctx, s=s)

@router.get('/api/proposals')
def proposals(status: Optional[str]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_proposals(status=status, ctx=ctx, s=s)

@router.get('/api/proposals/{pid}')
def proposal(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_proposal(pid=pid, ctx=ctx, s=s)

@router.post('/api/proposals/{pid}/send')
def send_proposal(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_send_proposal(pid=pid, ctx=ctx, s=s)

@router.post('/api/proposals/{pid}/reject')
def reject_proposal(pid: int, ctx=Depends(current), s: Session=Depends(db)):
 return _s_reject_proposal(pid=pid, ctx=ctx, s=s)

@router.post('/api/proposals/{pid}/accept')
def accept_proposal(pid: int, x: ProposalAcceptIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_accept_proposal(pid=pid, x=x, ctx=ctx, s=s)

@router.put('/api/targets')
def set_target(x: TargetIn, ctx=Depends(current), s: Session=Depends(db)):
 return _s_set_target(x=x, ctx=ctx, s=s)

@router.get('/api/targets')
def targets(period: Optional[str]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_targets(period=period, ctx=ctx, s=s)

@router.get('/api/targets/performance')
def target_performance(period: Optional[str]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_target_performance(period=period, ctx=ctx, s=s)

@router.get('/api/automation/funnel')
def funnel(start: Optional[date]=None, end: Optional[date]=None, owner_id: Optional[int]=None, ctx=Depends(current), s: Session=Depends(db)):
 return _s_funnel(start=start, end=end, owner_id=owner_id, ctx=ctx, s=s)

@router.post('/api/automation/run-reminders')
def run_reminders_now(ctx=Depends(current), s: Session=Depends(db)):
 return _s_run_reminders_now(ctx=ctx, s=s)
