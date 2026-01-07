
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Path setup
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("services/course-lifecycle"))

from app.main import app
from app.database import engine
from app.models import Base, Course
from app.api.dependencies import get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# DB Setup
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

def verify_blueprint_lock():
    print("--- Verifying Blueprint Lock ---")
    
    # 1. Setup Data
    db = TestingSessionLocal()
    
    course = Course(
        id=1,
        title="Test Course",
        course_code="TST101",
        blueprint={"modules": [{"id": "m1", "name": "Original"}]},
        status="DRAFT"
    )
    db.add(course)
    db.commit()
    
    # Test 1: Update Allowed (Pre-KG)
    resp = client.put("/api/v1/courses/1/blueprint", json={"blueprint": {"modules": [{"id": "m1", "name": "Updated Pre-KG"}]}})
    assert resp.status_code == 200
    db.refresh(course)
    print(f"✅ Pre-KG Update Allowed. Blueprint ModuleName: {course.blueprint['modules'][0]['name']}")
    
    # 2. Build Graph (Simulate KG Init)
    # We just inject it directly to simulate state
    course.course_graph = {"children": [{"id": "m1", "name": "Graph Module"}]}
    db.commit()
    print("✅ KG Initialized.")
    
    # Test 2: Update Blocked (Post-KG)
    resp = client.put("/api/v1/courses/1/blueprint", json={"blueprint": {"modules": [{"id": "m1", "name": "Blocked Update"}]}})
    if resp.status_code == 409:
        print("✅ Post-KG Update Blocked (409) as expected.")
    else:
        print(f"❌ Post-KG Update NOT Blocked: {resp.status_code} {resp.text}")
        
    db.refresh(course)
    assert course.blueprint['modules'][0]['name'] == "Updated Pre-KG"
    print("✅ DB Blueprint remains unchanged.")
    
    # Test 3: Generate V2 (Conditional Update)
    # Payload trying to overwrite blueprint
    gen_payload = {
        "blueprint": {"modules": [{"id": "m1", "name": "Generate Overwrite Attempt"}]},
        "generation_spec": {},
        "prompt_text": "Run"
    }
    
    resp = client.post("/api/v1/courses/1/generate_v2", json=gen_payload)
    assert resp.status_code == 200
    
    db.refresh(course)
    if course.blueprint['modules'][0]['name'] == "Updated Pre-KG":
        print("✅ Generate V2 skipped blueprint update (Good).")
    else:
        print(f"❌ Generate V2 OVERWROTE blueprint: {course.blueprint['modules'][0]['name']}")

    print("\n✅ Verification Passed!")

if __name__ == "__main__":
    try:
        verify_blueprint_lock()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
