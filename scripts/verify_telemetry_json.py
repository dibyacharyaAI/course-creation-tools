
import sys
import os
import shutil
import logging
from datetime import datetime
import json

# Setup Paths for direct import
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

from fastapi.testclient import TestClient
# Include parent dir so 'app' can be found
from app.main import app
from app.models import Course, JobRun, AuditEvent, Base

# Mock Kafka
import unittest.mock
sys.modules['shared.clients.kafka_client'] = unittest.mock.Mock()

def run_verification():
    print("🧪 Verifying Telemetry JSON Serialization...")
    
    # 1. Setup Test DB
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    test_engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    from app.api.dependencies import get_db
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    app.router.on_startup = [] # Disable real startup
    
    client = TestClient(app)
    
    # 2. Seed Data
    print("   [Setup] Seeding JobRun and AuditEvent...")
    db = TestingSessionLocal()
    course = Course(id=101, title="Telemetry Test Course")
    db.add(course)
    
    job = JobRun(
        course_id=101,
        job_type="TEST_JOB",
        status="COMPLETED",
        started_at=datetime.now(),
        duration_ms=500
    )
    db.add(job)
    
    audit = AuditEvent(
        course_id=101,
        action="TEST_ACTION",
        timestamp=datetime.now(),
        comment="Test Comment"
    )
    db.add(audit)
    db.commit()
    db.close()
    
    # 3. Call Endpoint
    print("   [Step] Calling GET /telemetry...")
    resp = client.get("/api/v1/courses/101/telemetry")
    
    print(f"   [Response] {resp.status_code}")
    if resp.status_code != 200:
        print(f"   ❌ Failed: {resp.text}")
        return

    data = resp.json()
    print("   [Data] Received JSON:")
    print(json.dumps(data, indent=2))
    
    # 4. Assertions
    if not isinstance(data.get("jobs"), list):
        print("   ❌ 'jobs' is not a list")
        return
        
    if not isinstance(data.get("audit_events"), list):
        print("   ❌ 'audit_events' is not a list")
        return
        
    job0 = data["jobs"][0]
    audit0 = data["audit_events"][0]
    
    # Check keys
    required_job_keys = {"id", "job_type", "status", "started_at"}
    if not required_job_keys.issubset(job0.keys()):
        print(f"   ❌ Job missing keys: {required_job_keys - set(job0.keys())}")
        return
        
    print("   ✅ JSON Structure Validated (Pydantic models working)")
    
if __name__ == "__main__":
    run_verification()
