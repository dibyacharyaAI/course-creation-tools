import sys
import os
import json
import logging
from unittest.mock import MagicMock, patch

# Manage sys.path dynamically to avoid 'app' collision
ai_auth_path = os.path.join(os.path.dirname(__file__), "../services/ai-authoring")
lifecycle_path = os.path.join(os.path.dirname(__file__), "../services/course-lifecycle")
shared_path = os.path.join(os.path.dirname(__file__), "..")

sys.path.append(shared_path)

# Mock shared.core.settings before imports
mock_settings = MagicMock()
mock_settings.DATABASE_URL = "sqlite:///:memory:"
mock_settings.GEMINI_API_KEY = "dummy"
sys.modules['shared.core.settings'] = MagicMock(settings=mock_settings)
sys.modules['shared.core.logging'] = MagicMock()
sys.modules['shared.clients.kafka_client'] = MagicMock()

# --- Unit Test PromptBuilder ---
print("--- Verifying PromptBuilder ---")
sys.path.insert(0, ai_auth_path)
from app.prompt_builder import PromptBuilder

def test_prompt_builder():
    spec = {"constraints": {"ppt": {"max_slides": 8}}}
    blueprint = {}
    
    concepts = ["Concept A", "Concept B"]
    prereqs = ["Prereq X"]
    
    pb = PromptBuilder(
        spec=spec, 
        blueprint=blueprint, 
        topic_context={"module_title": "M1", "topic_title": "T1"},
        key_concepts=concepts,
        prerequisites=prereqs
    )
    
    prompt = pb.build_topic_prompt()
    
    if "MUST explicitly cover these related concepts: Concept A, Concept B" in prompt:
        print("✅ PromptBuilder contains Key Concepts")
    else:
        print(f"❌ PromptBuilder FAILED to include Concepts. Prompt:\n{prompt}")
        sys.exit(1)

    if "Consider these prerequisites for context: Prereq X" in prompt:
        print("✅ PromptBuilder contains Prerequisites")
    else:
        print(f"❌ PromptBuilder FAILED to include Prerequisites")
        sys.exit(1)

test_prompt_builder()
print("--------------------------------")

# --- Cleanup for Next Test ---
sys.path.pop(0) # Remove ai_auth_path
# Remove cached 'app' modules to allow importing course-lifecycle's app
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

# --- Integration Test Logic (Simulated) ---
# We want to verify logic in courses.py without spin up full app if possible, 
# or use TestClient. TestClient is better.

print("--- Verifying Course Lifecycle Logic ---")
sys.path.insert(0, lifecycle_path)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQL_ALCHEMY_DATABASE_URL = "sqlite:///./test_kg_concepts.db"
engine = create_engine(SQL_ALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch create_engine to return our engine and avoid URL parsing issues with mocks
with patch("shared.db.base.create_engine", return_value=engine):
    # Import specific modules to ensure we get the right ones
    from app.models import Course, TopicGenerationJob, Base
    from app.api.dependencies import get_db
    from app.main import app

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the get_db used by routers
# We need to patch it WHERE it is imported.
# In `services/course-lifecycle/app/api/routers/courses.py`, it imports `requests`.

SQL_ALCHEMY_DATABASE_URL = "sqlite:///./test_kg_concepts.db"
engine = create_engine(SQL_ALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# We need to import app AFTER helper mocks
# To avoid complex shared deps, assuming mostly mocked above
# But earlier we had issues. Let's try.
from app.main import app
app.dependency_overrides[get_db] = override_get_db
app.router.on_startup.clear() # Skip startup

# Patch requests
@patch('app.api.routers.courses.requests.post')
def test_integration(mock_post):
    # Setup DB
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    db = TestingSessionLocal()
    
    # Create Course with Graph
    # 1 Concept: "Photosynthesis" (c_1)
    # 1 Topic: "Process of Photosynthesis" (t_1)
    # Relation: t_1 -> c_1 (RELATED_TO)
    
    c_graph = {
        "course_id": 1,
        "version": 1,
        "concepts": [
            {"id": "c_1", "label": "Photosynthesis", "tags": []},
            {"id": "c_2", "label": "Sunlight", "tags": []}
        ],
        "relations": [
            {"source_id": "t_1", "target_id": "c_1", "relation_type": "RELATED_TO"},
            {"target_id": "t_1", "source_id": "c_2", "relation_type": "PREREQUISITE"} 
            # c_2 is Prereq for t_1
        ],
        "children": [
            {"id": "m1", "name": "Module 1", "children": [
                {"id": "t1", "topic_id": "t_1", "title": "Process of Photosynthesis"}
            ]}
        ]
    }
    
    course = Course(
        id=1,
        title="Bio 101",
        course_graph=c_graph,
        course_graph_version=1,
        generation_spec={"constraints": {"ppt": {"max_slides": 8}}}
    )
    db.add(course)
    db.commit()
    db.close()
    
    # Set Env Var
    os.environ["ENABLE_KG_CONTEXT"] = "true"
    
    # Trigger Gen
    # Endpoint: /courses/{course_id}/topics/{topic_id}/ppt/generate
    # POST
    
    # Mock Response for AI Service
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"slides": []}
    
    res = client.post("/courses/1/topics/t_1/ppt/generate?auto_sync=false")
    
    if res.status_code != 200:
        print(f"❌ Request failed: {res.status_code} {res.text}")
        sys.exit(1)
        
    # Verify Payload
    # Mock_post called with url, json=payload
    args, kwargs = mock_post.call_args
    payload = kwargs.get("json")
    
    print("\nPayload Sent to AI-Authoring:")
    print(json.dumps(payload, indent=2))
    
    # Assertions
    if "key_concepts" not in payload:
        print("❌ Payload missing key_concepts")
        sys.exit(1)
        
    kcs = payload["key_concepts"]
    reqs = payload["prerequisites"]
    
    # t_1 -> c_1 (Photosynthesis) => Photosynthesis in Key Concepts
    # c_2 -> t_1 (Prereq) => Sunlight in Prereq AND Key Concepts (since we gather all linked)
    
    if "Photosynthesis" in kcs:
        print("✅ Concept 'Photosynthesis' extracted correctly")
    else:
        print("❌ 'Photosynthesis' missing from key_concepts")
        
    if "Sunlight" in reqs:
        print("✅ Prerequisite 'Sunlight' extracted correctly")
    else:
        print("❌ 'Sunlight' missing from prerequisites")

    print("\nVerify DONE.")

test_integration()
