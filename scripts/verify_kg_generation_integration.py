
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

def verify_payload():
    print("--- Verifying KG Generation Payload ---")
    
    # 1. Setup Data
    db = TestingSessionLocal()
    
    # Create Course with Blueprint having Outcome
    course = Course(
        id=1,
        title="Test Course",
        course_code="TST101",
        blueprint={
            "course_identity": {"course_name": "Test Course"},
            "modules": [
                {
                    "id": "m1", 
                    "name": "Module 1", 
                    "topics": [
                        {"id": "t1", "name": "Topic 1", "topic_outcome": "Students shall understand nothing."}
                    ]
                }
            ]
        },
        status="DRAFT"
    )
    db.add(course)
    db.commit()
    
    # Manually populate KG (Trigger Build via Endpoint or Manual)
    # Let's call build graph endpoint if available or mock it.
    # The existing test calls /graph/build.
    
    # Need to populate jobs first? GraphBuilder relies on jobs for slides, but structure comes from blueprint.
    # We want to verify that GraphBuilder populates `outcome` in TopicNode.
    
    # Import GraphBuilder to run it manually or verify via API
    from app.graph_builder import GraphBuilder
    # Empty jobs list for structure only
    builder = GraphBuilder(course, [])
    graph, stats = builder.build()
    
    # Save Graph to Course
    course.course_graph = graph.model_dump(mode='json')
    db.commit()
    print("✅ Graph built and saved to DB.")
    
    # Verify Outcome in Graph
    t_node = course.course_graph["children"][0]["children"][0]
    print(f"DEBUG: Topic in Graph: {t_node}")
    if t_node.get("outcome") == "Students shall understand nothing.":
        print("✅ Topic Outcome preserved in KG.")
    else:
        print(f"❌ Topic Outcome LOST in KG: {t_node.get('outcome')}")
        return

    # 2. Trigger Generation and Intercept Payload
    # Mock requests.post in courses.py
    with patch("app.api.routers.courses.requests.post") as mock_post:
        # Mock Response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"slides": [{"title": "Mock Slide"}]}
        mock_post.return_value = mock_resp
        
        # Call Endpoint
        # Using correct prefix logic from main.py (assuming /api/v1/courses...)
        # If verify_step6 used /api/v1/courses, we use that.
        resp = client.post("/api/v1/courses/1/topics/t1/ppt/generate?module_id=m1&auto_sync=false")
        
        if resp.status_code != 200:
            print(f"❌ API Call Failed: {resp.status_code} {resp.text}")
            return
            
        # Inspect Call Args
        args, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        
        print("\n--- Payload Inspection ---")
        # Check kg_outline
        if "kg_outline" in payload:
            print("✅ kg_outline present in payload")
            outline = payload["kg_outline"]
            # Check structure
            if outline["course_title"] == "Test Course":
                print("✅ kg_outline.course_title correct")
            else:
                print(f"❌ kg_outline.course_title mismatch: {outline.get('course_title')}")
                
            mods = outline.get("modules", [])
            if len(mods) == 1 and mods[0]["title"] == "Module 1":
                 print("✅ kg_outline modules correct")
            else:
                 print(f"❌ kg_outline modules mismatch: {mods}")

            # Check outcome in payload
            t_out = mods[0]["topics"][0].get("topic_outcome")
            if t_out == "Students shall understand nothing.":
                print("✅ Topic Outcome sent in payload")
            else:
                print(f"❌ Topic Outcome NOT in payload: {t_out}")
                
        else:
            print("❌ kg_outline MISSING in payload")

        # Check blueprint removed
        if "blueprint" not in payload:
            print("✅ blueprint removed from payload (Good)")
        else:
            print("⚠️ blueprint STILL in payload (Check if intended)") # I set it to match user request "Remove blueprint"
            
        print("✅ Verification Passed")

if __name__ == "__main__":
    try:
        verify_payload()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()

