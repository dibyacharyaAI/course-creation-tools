import requests
import json
import sys

# Internal URL when running inside the container
BASE_URL = "http://localhost:8000"
LC_URL = "http://course-lifecycle:8000"  # Lifecycle service for some endpoints if needed, but main gateway is 3000. 
# Inside ai-authoring container, we can access other services by hostname.
# The user wants "UI -> Backend Contract Test". UI hits gateway (:3000), which routes to services.
# But inside ai-authoring, we interpret "Backend" as the service itself (ai-authoring:8000) for the prompt build part,
# and course-lifecycle:8000 for the outline part.
# To keep it simple, we'll try to hit services directly where possible or use the gateway if accessible.
# Let's assume we run this script inside `infra-ai-authoring-1`.
# It can reach `course-lifecycle` at `http://course-lifecycle:8000`.

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg, details=""):
    print(f"❌ FAIL: {msg}")
    if details:
        print(f"   >> {details}")

def verify_full_stack():
    print("--- 🚀 STARTING FULL-STACK VERIFICATION ---")
    
    # ---------------------------------------------------------
    # TEST 1: UI -> Backend Contract Replica (Step 5 Payload)
    # ---------------------------------------------------------
    print("\n[TEST 1] UI Step 5 Contract Replica")
    
    # Reconstructing payload exactly as Step5Prompt.jsx does
    # Input: Blueprint with 2 modules, each 2 topics. 
    # Spec: Pedagogy Checklist, Output Constraints (Max 10, Bloom Global Default)
    
    payload = {
      "course_id": 999,
      "blueprint": {
        "course_identity": {
            "course_name": "Full Stack Test Course",
            "description": "Verification of End-to-End Contracts"
        },
        "modules": [
            {"id": "M1", "title": "Module A", "topics": [{"id": "T1", "name": "Topic A1"}, {"id": "T2", "name": "Topic A2"}]},
            {"id": "M2", "title": "Module B", "topics": [{"id": "T3", "name": "Topic B1"}]}
        ]
      },
      "generation_spec": {
        # This mimicks what is stored in DB by Step 4 and passed to Step 5
        "pedagogy_checklist": ["Case Studies", "Interactive Q&A"],
        "output_constraints": {
            "max_slides": 12,
            "font_size_min": 18,
            "word_limit": 50,
            "bloom_policy": {
                "global_default": "Evaluate",
                "overrides": {}
            }
        },
        "time_distribution": {
             "mode": "AUTO_WEIGHTED"
        },
        "hierarchy_scope": {
             "modules": [{"module_id": "M1"}, {"module_id": "M2"}]
        },
        "total_duration_minutes": 120
      },
      # Step 5 sends 'bloom' top-level too, derived from policy
      "bloom": {
          "default_level": "Evaluate",
          "overrides": {}
      }
    }
    
    # Target: POST /prompts/build (AI Authoring Service)
    # Inside ai-authoring container, this is localhost:8000
    try:
        res = requests.post(f"{BASE_URL}/prompts/build", json=payload)
        if res.status_code == 200:
            data = res.json()
            prompt = data.get("prompt_text", "")
            
            # Checks
            checks = [
                ("Pedagogy 'Case Studies'", "Case Studies" in prompt),
                ("Max Slides 12", "Max Slides: 12" in prompt),
                ("Bloom Default 'Evaluate'", "Default Level: Evaluate" in prompt),
                ("Modules Block Present", "Module A" in prompt and "Module B" in prompt)
            ]
            
            all_pass = True
            for name, passed in checks:
                if passed:
                    print_pass(f"Contract: {name}")
                else:
                    print_fail(f"Contract: {name}", "Not found in prompt text")
                    all_pass = False
            
            if all_pass:
                print(">> Test 1 Result: PASS")
            else:
                 print(">> Test 1 Result: FAIL")
        else:
            print_fail("Test 1 Request Failed", f"Status: {res.status_code}, Body: {res.text}")
    except Exception as e:
        print_fail(f"Test 1 Exception: {e}")

    # ---------------------------------------------------------
    # TEST 2: Outline Behavior (Lifecycle Service)
    # ---------------------------------------------------------
    print("\n[TEST 2] Outline Behavior (Deck Modes)")
    
    # We need to create a course first to test outline generation? 
    # Or can we use the /ppt/outline endpoint which might rely on DB state.
    # The /ppt/outline endpoint requires course_id and reads blueprint/specs from DB.
    # So we MUST create a course and save data first.
    
    # Strategy: Use `course-lifecycle` service directly.
    try:
        # A. Create Course
        lc_res = requests.post(f"{LC_URL}/courses", json={"title": "Outline Test", "description": "Deck Mode Check"})
        if lc_res.status_code not in [200, 201]:
             print_fail("Setup: Create Course", lc_res.text)
             return
        course_id = lc_res.json()["id"]
        print_pass(f"Setup: Course Created (ID: {course_id})")
        
        # B. Save Blueprint (Large enough to trigger truncation if limit is low)
        # 4 modules * 4 topics = 16 topics. Max slides 10.
        topics = [{"id": f"T{i}", "name": f"Topic {i}"} for i in range(4)]
        modules = [{"id": f"M{j}", "title": f"Mod {j}", "topics": topics} for j in range(4)]
        
        # Client uses PUT for blueprint
        bp_res = requests.put(f"{LC_URL}/courses/{course_id}/blueprint", json={"blueprint": {"modules": modules, "course": {"duration_minutes": 2400}}})
        if bp_res.status_code not in [200, 201]:
             print_fail("Setup: Save Blueprint", bp_res.text)
             return
             
        # C. Save Specs (Max 5 to force warnings/overflow)
        # Client uses POST /generation-spec
        # Payload usually: { course_id: int, ...spec_fields... }
        spec_payload = {
            "course_id": course_id,
            "total_duration_minutes": 2400,
            "output_constraints": {"max_slides": 5}, 
            "hierarchy_scope": {"modules": [{"module_id": m["id"]} for m in modules]}, # Select all
            "time_distribution": {"mode": "AUTO"}, # Required
            "pedagogy_checklist": ["Default"]      # Required
        }
        spec_res = requests.post(f"{LC_URL}/generation-spec", json=spec_payload)
        
        if spec_res.status_code not in [200, 201]:
             # Fallback check: older endpoint might be /courses/{id}/specs?
             spec_res = requests.post(f"{LC_URL}/courses/{course_id}/specs", json=spec_payload)
             if spec_res.status_code not in [200, 201]:
                 print_fail("Setup: Save Specs", spec_res.text)
                 return

        # D. Run QUICK_DECK
        qd_res = requests.post(f"{LC_URL}/ppt/outline", json={"course_id": course_id, "deck_mode": "QUICK_DECK"})
        if qd_res.status_code == 200:
            qd_data = qd_res.json()
            slides = qd_data.get("slides", [])
            warnings = qd_data.get("coverage_warnings", [])
            
            # Check 1: Slide count <= 10 + intro/outro margin? 
            # Actually generator usually adheres strictly or +1 for title.
            # Max 10 slides requested.
            count_ok = len(slides) <= 12 # Allow small buffer for title/divider
            
            # Check 2: Warnings present (since we have 16 topics but 10 slides)
            warn_ok = len(warnings) > 0
            
            if count_ok and warn_ok:
                print_pass(f"QUICK_DECK: count={len(slides)}, warnings={len(warnings)}")
            else:
                print_fail("QUICK_DECK Behavior", f"Count: {len(slides)}, Warnings: {len(warnings)}")
                
            # Check 3: Duration Semantics
            c_dur = qd_data.get("course_duration_minutes")
            d_dur = qd_data.get("deck_duration_minutes")
            if c_dur != d_dur:
                 print_pass(f"Duration Semantics: Course ({c_dur}) != Deck ({d_dur})")
            else:
                 print_fail("Duration Semantics", f"Course {c_dur} == Deck {d_dur} (Expected mismatch for Quick Deck)")

        else:
            print_fail("QUICK_DECK Request Failed", qd_res.text)
            
        # E. Run FULL_COVERAGE (Fail Case)
        fc_res = requests.post(f"{LC_URL}/ppt/outline", json={"course_id": course_id, "deck_mode": "FULL_COVERAGE"})
        if fc_res.status_code == 400:
            print_pass("FULL_COVERAGE: Correctly blocked (400)")
        else:
            print_fail("FULL_COVERAGE: Should fail but got", f"{fc_res.status_code}")

    except Exception as e:
        print_fail(f"Test 2 Exception: {e}")
        
    # ---------------------------------------------------------
    # TEST 3: Verifier Gate (Explicit)
    # ---------------------------------------------------------
    print("\n[TEST 3] Verifier Gate (Explicit Check)")
    # Use slides from Test 2 (QUICK_DECK)
    if 'qd_data' in locals() and qd_data.get("slides"):
        slides_to_verify = {"slides": qd_data["slides"]}
        
        try:
            # STRICT Mode (Should FAIL because we have 0 evidence and generator adds placeholders)
            strict_res = requests.post(f"{LC_URL}/ppt/verify", json={
                "slides": slides_to_verify,
                "strictness": "STRICT"
            })
            
            if strict_res.status_code == 200:
                rep = strict_res.json()
                if rep.get("status") == "FAIL":
                    print_pass("Verifier STRICT: Status is FAIL")
                else:
                    print_fail("Verifier STRICT", f"Expected FAIL, got {rep.get('status')}")
            else:
                print_fail("STRICT Request Failed", strict_res.text)
                
            # DRAFT Mode (Should PASS/WARN)
            draft_res = requests.post(f"{LC_URL}/ppt/verify", json={
                "slides": slides_to_verify,
                "strictness": "DRAFT"
            })
            
            if draft_res.status_code == 200:
                rep = draft_res.json()
                if rep.get("status") in ["PASS", "WARN"]:
                     print_pass(f"Verifier DRAFT: Status is {rep.get('status')}")
                else:
                     print_fail("Verifier DRAFT", f"Expected PASS/WARN, got {rep.get('status')}")
            else:
                print_fail("DRAFT Request Failed", draft_res.text)

        except Exception as e:
            print_fail(f"Test 3 Exception: {e}")
    else:
        print_fail("Test 3 Skipped", "No slides from Test 2")

if __name__ == "__main__":
    verify_full_stack()
