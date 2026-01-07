
import sys
import os
import json

# Add services to path
# Add specific service path
sys.path.append(os.path.abspath("services/ai-authoring"))

from app.prompt_builder import PromptBuilder

def test_prompt_builder_prefers_outline():
    # Setup
    blueprint = {
        "course": {"course_title": "Old Blueprint Title"},
        "modules": [
            {"name": "Old Module 1", "id": "m1", "topics": []}
        ]
    }
    
    kg_outline = {
        "course_title": "New KG Title",
        "modules": [
            {"title": "New KG Module 1", "id": "m1", "topics": []} # KG uses "title", Blueprint uses "name" (normalized to title in Builder)
        ]
    }
    
    spec = {"output_constraints": {}}
    
    # Test 1: With Outline
    builder = PromptBuilder(spec=spec, blueprint=blueprint, outline=kg_outline)
    user_prompt = builder.build_user_prompt()
    topic_prompt = builder.build_topic_prompt()
    
    # Assertions
    print("--- Test 1: With Outline ---")
    if "New KG Title" in user_prompt:
        print("✅ User Prompt uses KG Title")
    else:
        print(f"❌ User Prompt failed: {user_prompt[:100]}...")

    if "New KG Module 1" in user_prompt:
        print("✅ User Prompt lists KG Module")
    else:
        print(f"❌ User Prompt failed to list KG module")
        
    if "New KG Title" in topic_prompt:
        print("✅ Topic Prompt uses KG Title")
    else:
        print(f"❌ Topic Prompt failed: {topic_prompt[:100]}...")

    # Test 2: Without Outline (Fallback)
    builder_legacy = PromptBuilder(spec=spec, blueprint=blueprint, outline=None)
    user_prompt_legacy = builder_legacy.build_user_prompt()
    
    print("\n--- Test 2: Legacy Fallback ---")
    if "Old Blueprint Title" in user_prompt_legacy:
        print("✅ Legacy Prompt uses Blueprint Title")
    else:
        print("❌ Legacy Prompt failed")

if __name__ == "__main__":
    try:
        test_prompt_builder_prefers_outline()
        print("\nVerification Passed!")
    except ImportError as e:
        print(f"Import Error: {e}")
        # Adjust path if needed
    except Exception as e:
        print(f"Test Failed: {e}")
