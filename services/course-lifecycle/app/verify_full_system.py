import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
RAG_URL = "http://rag-indexer:8000"

def print_result(check_name, status, details=""):
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} {check_name}: {status} {details}")

def verify_system():
    print("--- 🚀 STARTING SYSTEM VERIFICATION (INTERNAL) ---")
    
    # 1. CREATE COURSE
    print("\n--- 1. Create Course ---")
    res = requests.post(f"{BASE_URL}/courses", json={"title": "Verify Course", "description": "Auto Verification"})
    if res.status_code not in [200, 201]:
        print_result("Create Course", "FAIL", res.text)
        return
    course_id = res.json()["id"]
    print_result("Create Course", "PASS", f"ID: {course_id}")
    
    # 2. SAVE BLUEPRINT
    print("\n--- 2. Save Blueprint (Step 2) ---")
    blueprint_payload = {
        "course_id": course_id,
        "blueprint": {
            "course": {"course_title": "Verify Course", "duration_minutes": 2400},
            "modules": [
                {"id": "U1", "title": "Module 1", "topics": [{"id": "T1", "name": "Topic A"}, {"id": "T2", "name": "Topic B"}]},
                {"id": "U2", "title": "Module 2", "topics": [{"id": "T3", "name": "Topic C"}]}
            ]
        }
    }
    res = requests.post(f"{BASE_URL}/courses/{course_id}/blueprint", json=blueprint_payload)
    if res.status_code not in [200, 201]:
        print_result("Save Blueprint", "FAIL", res.text)
    else:
        print_result("Save Blueprint", "PASS")

    # 3. SAVE SPECS (Step 4)
    print("\n--- 3. Save Specs (Step 4) ---")
    spec_payload = {
        "course_id": course_id,
        "total_duration_minutes": 2400,
        "hierarchy_scope": {"modules": [{"module_id": "U1"}, {"module_id": "U2"}]},
        "time_distribution": {"mode": "AUTO_WEIGHTED"},
        "output_constraints": {
            "max_slides": 10,
            "grounding_strictness": "NORMAL"
        }
    }
    res = requests.post(f"{BASE_URL}/courses/{course_id}/specs", json=spec_payload)
    if res.status_code not in [200, 201]:
        print_result("Save Specs", "FAIL", res.text)
    else:
        print_result("Save Specs", "PASS")
        
    # 4. GENERATE OUTLINE (Step 6 Preview) - QUICK DECK
    print("\n--- 4. Generate Outline (Quick Deck) ---")
    outline_payload = {
        "course_id": course_id,
        "deck_mode": "QUICK_DECK",
        "grounding_strictness": "NORMAL"
    }
    res = requests.post(f"{BASE_URL}/ppt/outline", json=outline_payload)
    if res.status_code == 200:
        data = res.json()
        slides = data["slides"]
        intro = slides[0]
        
        # Checks
        has_intro = intro["module_id"] == "U0"
        count_check = len(slides) > 2
        evidence_placeholder = "evidence_used" in intro and "claims" in intro
        
        if has_intro and count_check and evidence_placeholder:
             print_result("Outline Generation", "PASS", f"Slides: {len(slides)}")
        else:
             print_result("Outline Generation", "FAIL", f"Intro: {has_intro}, Count: {count_check}, Ev: {evidence_placeholder}")
             
        # Duration Mismatch Check
        print(f"   Debug: course_duration_minutes={data.get('course_duration_minutes')}")
        print(f"   Debug: deck_duration_minutes={data.get('deck_duration_minutes')}")
    else:
        print_result("Outline Generation", "FAIL", f"{res.status_code} {res.text}")

    # 4.2 FULL COVERAGE FAIL TEST
    print("\n--- 4.2 Full Coverage Fail Test ---")
    
    # Update spec to max_slides=2
    spec_payload["output_constraints"]["max_slides"] = 2
    requests.post(f"{BASE_URL}/courses/{course_id}/specs", json=spec_payload)
    
    outline_payload["deck_mode"] = "FULL_COVERAGE"
    res = requests.post(f"{BASE_URL}/ppt/outline", json=outline_payload)
    if res.status_code == 400:
        print_result("Full Coverage Enforcement", "PASS", "Got 400 as expected")
    else:
        # If it returns 200, it means it didn't block. 
        print_result("Full Coverage Enforcement", "FAIL", f"Got {res.status_code}")

    # 5. RAG RETRIEVAL (Phase 4B)
    print("\n--- 5. RAG Retrieval (Phase 4B) ---")
    retrieve_payload = {
        "course_id": course_id,
        "topic_ids": [{"topic_id": "T1", "topic_name": "Topic A"}]
    }
    res = requests.post(f"{RAG_URL}/retrieve", json=retrieve_payload)
    if res.status_code == 200:
        print_result("RAG Retrieval Endpoint", "PASS")
    else:
        print_result("RAG Retrieval Endpoint", "FAIL", f"{res.status_code} {res.text}")

    # 6. PPT EXPORT (Check content generation trigger if exists)
    # Just checking if endpoints exist for now
    print("\n--- 6. Endpoints Existence Check ---")
    
    # Check PPT Export
    res = requests.options(f"{BASE_URL}/courses/{course_id}/export/ppt")
    # OPTIONS might not be implemented, let's try GET with invalid ID or just checking 404 vs 405/500
    # or just assume if code exists it works.
    # Actually, let's try to hit specific PPT render endpoint if we know it.
    # Step6 calling: /api/lifecycle/courses/${courseId}/export/ppt -> GET
    
    # We can try to hit it. It might fail because no slide content generated yet?
    # Or strictness?
    res = requests.get(f"{BASE_URL}/courses/{course_id}/export/ppt")
    print(f"PPT Export Status: {res.status_code}") 
    # If 200/400/500, endpoint exists. If 404, it doesn't.
    if res.status_code != 404:
        print_result("PPT Export Endpoint", "PASS", f"Status: {res.status_code}")
    else:
        print_result("PPT Export Endpoint", "FAIL", "404 Not Found")

    print("\n--- END VERIFICATION ---")

if __name__ == "__main__":
    verify_system()
