import sys
import os
import shutil
import logging
from datetime import datetime

# Setup Paths for direct import
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

from fastapi.testclient import TestClient
# Include parent dir so 'app' can be found
from app.main import app
from app.database import SessionLocal, engine
from app.models import Base, Course, TopicGenerationJob, JobRun, AuditEvent

# Mock Kafka
import unittest.mock
sys.modules['shared.clients.kafka_client'] = unittest.mock.Mock()

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEMO")

def run_demo():
    print("🎬 Starting E2E Demo (No Docker)...")
    
    # 1. Setup Test DB (In-Memory SQLite for Clean State)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use SQLite for persistence in file to debug if needed, or memory
    # memory is safest for stateless run
    print("   [Setup] Creating In-Memory DB...")
    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Override Dependency
    from app.api.dependencies import get_db
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    # DISABLE STARTUP EVENTS (Avoid real DB connection)
    app.router.on_startup = []
    
    with TestClient(app) as client:
        # 2. Create Course (Seed)
        print("\n   [Step 1] Creating Course...")
        db = TestingSessionLocal()
        course = Course(
            id=999, 
            title="Demo Course", 
            blueprint={"modules": [{"id": "m1", "topics": [{"id": "t1"}, {"id": "t2"}]}]}
        )
        course.course_graph = None # Start empty
        db.add(course)
        db.commit()
        db.close()
        
        # 3. Generate Topics (Task A Verification)
        print("   [Step 2] Generating Topics (Testing Linkage)...")
        # Trigger T1 (Should infer m1)
        resp = client.post("/api/v1/courses/999/topics/t1/ppt/generate")
        assert resp.status_code == 200, f"Generate T1 failed: {resp.text}"
        data = resp.json()
        assert data["module_id"] == "m1", f"Module ID inference failed. Got {data.get('module_id')}"
        print(f"     ✅ T1 Generated linked to {data['module_id']}")

        # Trigger T2 (Verify flow)
        client.post("/api/v1/courses/999/topics/t2/ppt/generate")
        
        # Verify/Mark them as READY (Simulate LLM completion)
        print("   [Step 3] Verifying Topics...")
        client.post("/api/v1/courses/999/topics/t1/ppt/verify")
        client.post("/api/v1/courses/999/topics/t2/ppt/verify")
        
        # 4. Build Graph
        print("\n   [Step 4] Building Graph (Testing Telemetry)...")
        resp = client.post("/api/v1/courses/999/graph/build")
        assert resp.status_code == 200, f"Build failed: {resp.text}"
        print("     ✅ Graph Built.")
        
        # Check Linkage in Graph
        graph_resp = client.get("/api/v1/courses/999/graph")
        graph = graph_resp.json()
        # Expect m1 -> t1, t2
        has_t1 = any(t['topic_id'] == 't1' for m in graph['children'] for t in m['children'])
        assert has_t1, "Topic T1 not found in graph! Linkage broken?"
        print("     ✅ Graph Linkage Confirmed.")

        # 5. Export Gate Check (Task C)
        print("\n   [Step 5] Testing Export Gate (Expect 422)...")
        resp = client.post("/api/v1/courses/999/export/pdf")
        if resp.status_code == 422:
            print("     ✅ Export connection blocked as expected (Unapproved topics).")
        else:
            print(f"     ❌ Export should have failed! Got {resp.status_code}")
        
        # 6. Approve Topic T1
        print("\n   [Step 6] Approving Topic T1...")
        approval_payload = {
            "status": "APPROVED",
            "timestamp": datetime.now().isoformat(),
            "comment": "Looks good"
        }
        resp = client.post("/api/v1/courses/999/topics/t1/approve", json=approval_payload)
        assert resp.status_code == 200, f"Approve failed: {resp.text}"
        
        # 7. Export Again (Should still fail because T2 is not approved)
        print("   [Step 7] Testing Export Gate Partial (Expect 422)...")
        resp = client.post("/api/v1/courses/999/export/pdf")
        assert resp.status_code == 422, "Should still be blocked by T2"
        print("     ✅ Blocked by T2.")
        
        # Approve T2
        client.post("/api/v1/courses/999/topics/t2/approve", json=approval_payload)
        
        # 8. Export Success
        print("\n   [Step 8] Testing Export Success...")
        resp = client.post("/api/v1/courses/999/export/pdf")
        assert resp.status_code == 200, f"Export failed: {resp.text}"
        print(f"     ✅ Output: {resp.json()}")

        # 9. Verify Telemetry (Task B)
        print("\n   [Step 9] Verifying Telemetry...")
        resp = client.get("/api/v1/courses/999/telemetry")
        telemetry = resp.json()
        jobs = telemetry['jobs']
        audits = telemetry['audit_events']
        
        print(f"     Found {len(jobs)} Jobs, {len(audits)} Audits")
        
        # Expect: GENERATE(2), VERIFY(2), BUILD(1), EXPORT_PDF(3: blocked, blocked, completed), 
        job_types = [j['job_type'] for j in jobs]
        print(f"     Job Types: {job_types}")
        
        assert "BUILD" in job_types
        assert "EXPORT_PDF" in job_types
        assert "GENERATE" in job_types
        
        # Check Audit Sync
        audit_actions = [a['action'] for a in audits]
        assert "APPROVED" in audit_actions
        print("     ✅ Telemetry verified.")
        
        print("\n🎉 DEMO COMPLETE: All Production Gaps Verified.")

if __name__ == "__main__":
    run_demo()
