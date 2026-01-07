import sys
import os
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Fix paths
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("services/course-lifecycle"))

from app.main import app
from app.database import engine
from app.models import Base, Course, TopicGenerationJob
from app.api.dependencies import get_db

# In-memory DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def verify_flow():
    print("\n=== Client Demo Flow Verification ===")

    # 1. Setup Data
    db = TestingSessionLocal()
    course = Course(
        id=99,
        title="Demo Course",
        blueprint={"modules": [{"id": "m1", "title": "Module 1", "topics": [{"id": "t1", "name": "Topic 1"}]}]}
    )
    db.add(course)
    
    slides = [
        {"slide_no": i+1, "title": f"Slide {i+1}", "bullets": ["A", "B"], "illustration_prompt": "A prompt"}
        for i in range(8)
    ]
    job = TopicGenerationJob(
        course_id=99,
        topic_id="t1",
        module_id="m1",
        status="GENERATED",
        slides_json={"slides": slides}
    )
    db.add(job)
    db.commit()
    db.close()
    print("✅ Fixtures created.")

    # 3. Build Graph
    resp = client.post("/api/v1/courses/99/graph/build")
    assert resp.status_code == 200
    print("✅ Graph Built.")

    # 4. Get Graph & Check ID Persistence
    resp = client.get("/api/v1/courses/99/graph")
    data = resp.json()
    slide_id_1 = data["children"][0]["children"][0]["children"][0]["children"][0]["id"]
    
    # Rebuild
    client.post("/api/v1/courses/99/graph/build")
    resp = client.get("/api/v1/courses/99/graph")
    slide_id_2 = resp.json()["children"][0]["children"][0]["children"][0]["children"][0]["id"]
    
    assert slide_id_1 == slide_id_2, "IDs must be stable across rebuilds"
    print(f"✅ ID Stability Verified: {slide_id_1}")

    # 5. Patch Slide
    resp = client.patch(f"/api/v1/courses/99/topics/t1/slides/{slide_id_1}", json={"bullets": ["A", "B", "Edited"]})
    assert resp.status_code == 200
    print("✅ Slide Patched.")

    # 6. Validate Graph
    resp = client.post("/api/v1/courses/99/graph/validate")
    assert resp.status_code == 200
    v_data = resp.json()
    if not v_data["valid"]:
        print(f"❌ FATAL: Validation Failed: {v_data['errors']}")
        sys.exit(1)
    assert v_data["valid"] == True
    print("✅ Graph Validated.")

    # 7. Approve Topic
    resp = client.post("/api/v1/courses/99/topics/t1/approve", json={"status": "APPROVED", "comment": "Great content"})
    assert resp.status_code == 200
    print("✅ Topic Approved.")

    # 8. Export PDF (GET)
    # Check if download endpoint works (even if it 500s due to missing deps, we want to confirm route)
    resp = client.get("/api/v1/courses/99/export/pdf?topic_id=t1")
    # Depending on env, PDFBuilder might fail or succeed. 
    # If it fails with 500, it's acceptable for this script if correct 500 is returned (e.g. library missing).
    # But ideally it returns 200 if dependencies installed.
    # We accept 200 or 500 (if error logged).
    if resp.status_code == 200:
        assert resp.headers["content-type"] == "application/pdf"
        print("✅ Export PDF (Topic) returned PDF.")
    else:
        print(f"❌ FATAL: Export PDF (Topic) returned {resp.status_code}. (Check logs: {resp.text})")
        sys.exit(1)

    # 9. Telemetry
    resp = client.get("/api/v1/courses/99/telemetry")
    assert resp.status_code == 200
    telemetry_data = resp.json()
    
    audit_events = telemetry_data.get("audit_events", [])
    has_audit = any(e.get("action") == "APPROVED" for e in audit_events)
    
    if not has_audit:
        print(f"❌ FATAL: Telemetry missing Approval Audit Event. Found: {audit_events}")
        sys.exit(1)
    
    print("✅ Telemetry Verified (Audit Event found).")

    print("\n=== ALL CHECKS PASSED ===")

if __name__ == "__main__":
    try:
        verify_flow()
    except AssertionError as e:
        print(f"\n❌ FAIL: Assertion Error: {e}")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ FATAL: Unexpected Error: {e}")
        sys.exit(1)
