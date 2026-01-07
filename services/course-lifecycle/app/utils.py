import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .models import JobRun, AuditEvent

logger = logging.getLogger(__name__)

def log_telemetry(event_name: str, course_code: str, details: dict = None):
    """
    Log telemetry event. 
    In future, this should write to AuditEvent or external collector.
    For now, structured logging.
    """
    if details is None:
        details = {}
        
    payload = {
        "event": event_name,
        "course_code": course_code,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    logger.info(f"TELEMETRY: {json.dumps(payload)}")

def create_db_job_run(db: Session, course_id: int, job_type: str, status: str, topic_id: str = None, duration_ms: int = 0, error_details: str = None):
    """Create a persistent JobRun in the DB"""
    try:
        run = JobRun(
            course_id=course_id,
            topic_id=topic_id,
            job_type=job_type,
            status=status,
            duration_ms=duration_ms,
            error_details=error_details,
            started_at=datetime.now() if duration_ms == 0 else datetime.fromtimestamp(datetime.now().timestamp() - (duration_ms / 1000.0)),
            ended_at=datetime.now()
        )
        db.add(run)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write JobRun: {e}")

def create_db_audit_event(db: Session, course_id: int, action: str, actor_id: str = "system", topic_id: str = None, comment: str = None):
    """Create a persistent AuditEvent in the DB"""
    try:
        event = AuditEvent(
            course_id=course_id,
            topic_id=topic_id,
            action=action,
            actor_id=actor_id,
            comment=comment,
            timestamp=datetime.now()
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write AuditEvent: {e}")
