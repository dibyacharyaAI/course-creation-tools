import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/lifecycle"
# Assuming Docker is running and mapped. If not, we might need to use localhost:8000 directly if services are up.
# The user env says "mapped in docker-compose". 
# But I can also import app directly if I want to avoid network.
# Using network is better for "client" simulation.

def create_course():
    logger.info("Creating Test Course...")
    res = requests.post(f"{BASE_URL}/courses", json={
        "title": "Optimistic Locking Test",
        "audience": "Developers",
        "topic": "Concurrency"
    })
    res.raise_for_status()
    course_id = res.json()["id"]
    logger.info(f"Created Course ID: {course_id}")
    return course_id

def verify_locking():
    course_id = 999 # Placeholder, need real ID or mock
    # Actually, let's try to find an existing course or create one via API if possible.
    # Since I don't want to depend on running services if they are not up, 
    # and previous scripts used direct DB/App imports, maybe I should do that?
    # But "Client" simulation is best done via API or MockClient. 
    # Given I modified `graph.py`, I can unit test the router logic directly by mocking DB?
    # Or I can use `TestClient` from FastAPI.
    
    pass

# Redoing with FastAPI TestClient for robust local verification without needing running server
import os
os.environ["TEST_MODE"] = "true"
sys.path.append(os.path.join(os.path.dirname(__file__), "../services/course-lifecycle"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..")) # For shared module if at root
# Or if shared is inside services?
# Let's list repo root to be sure.

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Course, TopicGenerationJob, Base

SQL_ALCHEMY_DATABASE_URL = "sqlite:///./test_mvcc.db"
engine = create_engine(SQL_ALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# We need to import the EXACT function that routers use for dependency injection
# graph.py imports get_db from ..dependencies (app.api.dependencies)
import app.api.dependencies as app_dependencies

# Patch engines to prevent connection to Postgres
import app.main as app_main
import app.database as app_database
app_main.engine = engine
app_database.engine = engine

# Override the get_db used by routers
app.dependency_overrides[app_dependencies.get_db] = override_get_db

# Disable startup events to prevent main.py from trying to connect to real Postgres/Kafka
logger.info(f"Startup handlers before clear: {len(app.router.on_startup)}")
app.router.on_startup.clear()
logger.info(f"Startup handlers after clear: {len(app.router.on_startup)}")

def run_test():
    # Setup DB
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    # 1. Create Course
    logger.info("--- Setup: Creating Course ---")
    course_data = {
        "title": "MVCC Test",
        "audience": "Testers",
        "topic": "Locking"
    }
    # Create manually in DB to skip auth/etc if needed, or use API
    # API create requires minimal data. 
    # NOTE: The create endpoint in `courses.py` might trigger background jobs. 
    # Let's insert directly to control state.
    
    db = TestingSessionLocal()
    course = Course(
        title="MVCC Test",
        course_graph_version=1,
        course_graph={
            "course_id": 1, 
            "version": 1,
            "children": [
                {
                    "id": "m1", "name": "Module 1", "children": [
                        {
                            "id": "t1", "topic_id": "topic_1", "title": "Topic 1", "status": "GENERATED", 
                            "children": [
                                {
                                    "id": "sub1", "title": "Sub", "children": [
                                        {
                                            "id": "slide_1", 
                                            "title": "Slide 1",
                                            "bullets": ["A", "B"],
                                            "order": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "concepts": [],
            "relations": []
        }
    )
    db.add(course)
    db.commit()
    course_id = course.id
    logger.info(f"Created Course {course_id} with Graph v1")
    db.close()
    
    # 2. Actor A fetches Graph
    logger.info("--- Step 2: Actor A fetches Graph ---")
    res = client.get(f"/courses/{course_id}/graph")
    if res.status_code != 200:
        logger.error(f"Failed to get graph: {res.status_code} {res.text}")
        sys.exit(1)
    graph_a = res.json()
    version_a = graph_a["version"]
    logger.info(f"Actor A holds version: {version_a}")
    
    # 3. Actor B fetches Graph
    logger.info("--- Step 3: Actor B fetches Graph ---")
    res = client.get(f"/courses/{course_id}/graph")
    graph_b = res.json()
    version_b = graph_b["version"]
    logger.info(f"Actor B holds version: {version_b}")
    
    # 4. Actor A Updates Slide (Success)
    logger.info("--- Step 4: Actor A patches Slide ---")
    patch_payload = {
        "title": "Slide 1 Edited by A"
    }
    # API: PATCH /.../slides/{slideId}?expected_version=X
    res = client.patch(
        f"/courses/{course_id}/topics/topic_1/slides/slide_1",
        json=patch_payload,
        params={"expected_version": version_a}
    )
    if res.status_code == 200:
        logger.info("✅ Actor A Update Success")
        new_graph = res.json()
        logger.info(f"New Graph Version: {new_graph['version']}")
    else:
        logger.error(f"❌ Actor A Update Failed: {res.text}")
        sys.exit(1)
        
    # 5. Actor B Updates Slide (Expect Failure)
    logger.info("--- Step 5: Actor B patches Slide (Stale Version) ---")
    patch_payload_b = {
        "title": "Slide 1 Edited by B"
    }
    res = client.patch(
        f"/courses/{course_id}/topics/topic_1/slides/slide_1",
        json=patch_payload_b,
        params={"expected_version": version_b} # Sending OLD version 1
    )
    
    if res.status_code == 409:
        logger.info("✅ Actor B Update Blocked (409 Conflict) as expected")
        logger.info(f"Error: {res.json()['detail']}")
    else:
        logger.error(f"❌ Actor B Update should have failed but got: {res.status_code}")
        # sys.exit(1) # Continue to KG test?? No, strict pass.
        sys.exit(1)
        
    # 6. Actor B Refreshes and Updates
    logger.info("--- Step 6: Actor B Refreshes and Retries ---")
    res = client.get(f"/courses/{course_id}/graph")
    graph_b_new = res.json()
    version_b_new = graph_b_new["version"]
    logger.info(f"Actor B refreshed. New Version: {version_b_new}")
    
    res = client.patch(
        f"/courses/{course_id}/topics/topic_1/slides/slide_1",
        json=patch_payload_b,
        params={"expected_version": version_b_new}
    )
    if res.status_code == 200:
         logger.info("✅ Actor B Update Success after Refresh")
    else:
         logger.error(f"❌ Actor B Retry Failed: {res.text}")
         sys.exit(1)

    logger.info("--- Verify KG Layer Locking ---")
    # 7. KG Update Locking
    res = client.get(f"/courses/{course_id}/kg")
    if res.status_code != 200:
         logger.error(f"Get KG Failed: {res.text}")
    kg_model = res.json()
    kg_ver = kg_model["version"]
    logger.info(f"KG Version: {kg_ver}")
    
    # Conflict test
    res = client.patch(
        f"/courses/{course_id}/kg",
        json={"concepts": [], "relations": []},
        params={"expected_version": kg_ver - 1} # Artificially old
    )
    if res.status_code == 409:
        logger.info("✅ KG Update Blocked (409) with stale version")
    else:
        logger.error(f"❌ KG Update should have failed: {res.status_code}")
        
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    logger.info("verification_complete")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        logger.error(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
