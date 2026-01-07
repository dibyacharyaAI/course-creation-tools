import requests
import json
import sys

# Internal URL when running inside the container
BASE_URL = "http://localhost:8000"

def verify_normalization():
    print("--- 🧪 STARTING NORMALIZATION VERIFICATION ---")

    # Payload mimicking Frontend Step 4/5 output
    payload = {
        "course_id": 999,
        "blueprint": {
            "course_identity": {
                "course_name": "Normalization Test Course",
                "description": "Testing payload normalization"
            },
            "modules": [
                {
                    "id": "M1",
                    "title": "Module 1",
                    "topics": [
                        {"id": "T1", "name": "Topic 1", "topic_outcome": "Understand basic normalization"}
                    ]
                }
            ]
        },
        "generation_spec": {
            # Legacy/Frontend fields
            "pedagogy_checklist": ["Socratic Method", "Real-world Examples"],
            "output_constraints": {
                "max_slides": 12,
                "font_size_min": 14,
                "bloom_policy": {
                    "global_default": "Analyze"
                }
            },
            "hierarchy_scope": {
                "modules": [{"module_id": "M1"}]
            }
        },
        # "bloom": None  <-- Intentionally omitted to testfallback
    }

    print(f"DTO Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        res = requests.post(f"{BASE_URL}/prompts/build", json=payload)
        
        if res.status_code != 200:
            print(f"❌ Failed to build prompt. Status: {res.status_code}")
            print(res.text)
            sys.exit(1)
            
        data = res.json()
        prompt_text = data.get("prompt_text", "")
        
        print("\n--- PROMPT GENERATED ---")
        # print(prompt_text[:500] + "...") # Print snippet
        
        # Assertions
        failures = []
        
        # 1. Pedagogy Check
        if "Socratic Method" in prompt_text and "Real-world Examples" in prompt_text:
             print("✅ Pedagogy Normalization: PASS")
        else:
             failures.append("Pedagogy items missing from prompt")
             print("❌ Pedagogy Normalization: FAIL")
             
        # 2. Max Slides Check
        # The prompt template uses: "- Max Slides: {constraints.get('ppt', {}).get('max_slides', 20)}"
        if "Max Slides: 12" in prompt_text:
             print("✅ Max Slides Normalization: PASS")
        else:
             failures.append("Max Slides (12) not found in prompt")
             print("❌ Max Slides Normalization: FAIL")
             
        # 3. Bloom Default Check
        # The prompt template uses: "Default Level: {default_bloom}"
        if "Default Level: Analyze" in prompt_text:
             print("✅ Bloom Default Normalization: PASS")
        else:
             failures.append("Bloom Default (Analyze) not found in prompt")
             print("❌ Bloom Default Normalization: FAIL")
             
        if failures:
            print(f"\nFAILED with {len(failures)} errors.")
            sys.exit(1)
        else:
            print("\n🎉 ALL CHECKS PASSED")

    except Exception as e:
        print(f"❌ Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_normalization()
