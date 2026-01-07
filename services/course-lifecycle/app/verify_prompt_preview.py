
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add repo root to path to import shared
sys.path.append(os.getcwd())
# Add course-lifecycle root to path to import app package
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

# Mock DB connection before importing app.main because main.py connects on module level
sys.modules["shared.db.base"] = MagicMock()
sys.modules["shared.db.base"].get_db_engine.return_value = MagicMock()
sys.modules["shared.db.base"].get_session_local.return_value = MagicMock()
sys.modules["shared.db.base"].Base = MagicMock()
# Also need to mock KafkaClient if it connects on startup?
# Startups are in @app.on_event("startup"), which TestClient calls.
# We also need to mock setup_logging potentially?
# Let's import shared.core.logging first
pass

from fastapi.testclient import TestClient
# Now import app.main
from app.main import app, get_db

# Mock DB
mock_db = MagicMock()
mock_course = MagicMock()
mock_course.id = 1
mock_course.course_code = "CS101"
mock_course.blueprint = {"modules": []} # Minimal blueprint
mock_course.generation_spec = {}
mock_db.query.return_value.filter.return_value.first.return_value = mock_course

def override_get_db():
    try:
        yield mock_db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@patch("app.main.Course")
def test_draft_prompt_preview(MockCourse):
    print("Testing POST /prompt/draft ...")
    
    # Setup Mock Course Class
    # Ensure Course.id can be accessed without error
    # When filter(Course.id == X) is called, Course.id is evaluated.
    MockCourse.id = MagicMock()

    # Mock Payload matching Frontend Step 5
    # Frontend sends generation_spec with hierarchy_scope inside
    payload = {
        "course_id": 1,
        "bloom": {"default_level": "Apply"},
        "generation_spec": {
            "hierarchy_scope": {
                "modules": [
                    {"module_id": "MOD1", "module_name": "Intro to AI"}
                ]
            }
        }
    }

    # Mock success response from ai-authoring
    mock_prompt_text = "Output JSON\nmax_slides: 10\ngrounding_strictness: HIGH\nThis is a mocked prompt."
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "prompt_text": mock_prompt_text,
        "metadata": {},
        "context_snippet": "..."
    }

    # Patch httpx.AsyncClient.post
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        # Test Sync/Async via TestClient
        # Note: TestClient handles async endpoints automatically
        response = client.post("/prompt/draft", json=payload)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            sys.exit(1)
            
        data = response.json()
        prompt_text = data.get("prompt_text", "")
        
        print(f"Prompt Length: {len(prompt_text)}")
        
        # Assertions
        assert "prompt_text" in data
        assert len(prompt_text) > 10
        assert "Output JSON" in prompt_text
        assert "max_slides" in prompt_text
        
        print("✅ /prompt/draft verification passed!")

if __name__ == "__main__":
    try:
        test_draft_prompt_preview()
    except AssertionError as e:
        print(f"❌ Assertion Failed: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")
        sys.exit(1)
