from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from ..dependencies import get_db
from ...models import JobRun, AuditEvent, TopicGenerationJob

router = APIRouter()

class JobRunResponse(BaseModel):
    id: int
    course_id: int
    topic_id: Optional[str] = None
    job_type: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = 0
    error_details: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AuditEventResponse(BaseModel):
    id: int
    course_id: int
    topic_id: Optional[str] = None
    action: str
    actor_id: Optional[str] = None
    timestamp: datetime
    comment: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class TelemetryResponse(BaseModel):
    jobs: List[JobRunResponse]
    audit_events: List[AuditEventResponse]

@router.get("/courses/{course_id}/telemetry", response_model=TelemetryResponse)
async def get_course_telemetry(course_id: int, db: Session = Depends(get_db)):
    """Get Timeline of Jobs and Audits"""
    jobs = db.query(JobRun).filter(JobRun.course_id == course_id).order_by(desc(JobRun.started_at)).limit(50).all()
    audits = db.query(AuditEvent).filter(AuditEvent.course_id == course_id).order_by(desc(AuditEvent.timestamp)).limit(50).all()
    
    return {
        "jobs": jobs,
        "audit_events": audits
    }

@router.get("/courses/{course_id}/topics/{topic_id}/telemetry", response_model=TelemetryResponse)
async def get_topic_telemetry(course_id: int, topic_id: str, db: Session = Depends(get_db)):
    """Get Telemetry for specific topic"""
    jobs = db.query(JobRun).filter(JobRun.course_id == course_id, JobRun.topic_id == topic_id).order_by(desc(JobRun.started_at)).all()
    audits = db.query(AuditEvent).filter(AuditEvent.course_id == course_id, AuditEvent.topic_id == topic_id).order_by(desc(AuditEvent.timestamp)).all()
    
    return {
        "jobs": jobs,
        "audit_events": audits
    }

class TimelineEvent(BaseModel):
    id: str
    type: str # AUDIT | EDIT | JOB
    timestamp: datetime
    summary: str
    details: Optional[dict] = None

@router.get("/courses/{course_id}/audit", response_model=List[TimelineEvent])
async def get_course_audit_timeline(course_id: int, db: Session = Depends(get_db)):
    """Unified Audit Timeline (Approvals, Edits, Jobs)"""
    from ...models import GraphEditLog
    
    events = []
    
    # 1. Audit Events (Approvals)
    audits = db.query(AuditEvent).filter(AuditEvent.course_id == course_id).all()
    for a in audits:
        events.append(TimelineEvent(
            id=f"audit_{a.id}",
            type="AUDIT",
            timestamp=a.timestamp,
            summary=f"{a.action} Topic {a.topic_id}",
            details={"actor": a.actor_id, "comment": a.comment}
        ))
        
    # 2. Graph Edit Logs
    edits = db.query(GraphEditLog).filter(GraphEditLog.course_id == course_id).all()
    for e in edits:
        events.append(TimelineEvent(
            id=f"edit_{e.id}",
            type="EDIT",
            timestamp=e.timestamp,
            summary=f"{e.operation} {e.target_id}",
            details=e.changes or {}
        ))
        
    # 3. Jobs (Significant ones)
    jobs = db.query(JobRun).filter(JobRun.course_id == course_id).all()
    for j in jobs:
        events.append(TimelineEvent(
            id=f"job_{j.id}",
            type="JOB",
            timestamp=j.started_at,
            summary=f"Job {j.job_type} - {j.status}",
            details={"duration": j.duration_ms, "error": j.error_details, "topic": j.topic_id}
        ))

    # Sort by timestamp desc
    events.sort(key=lambda x: x.timestamp, reverse=True)
    
    return events
