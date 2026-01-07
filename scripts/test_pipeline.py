
import requests
import time
import json

BASE_URL = "http://localhost:8001" # Course Lifecycle Port mapping from docker-compose
AUTH_URL = "http://localhost:8000" # Not used directly here, but for context

def step(msg):
    print(f"👉 {msg}")

def main():
    print("🚀 Starting Pipeline Verification Test")
    
    # 1. Check Health
    try:
        r = requests.get(f"{BASE_URL}/health")
        if r.status_code != 200:
            print("❌ Service not healthy")
            return
        print("✅ Service Health OK")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # 2. List Templates
    step("Fetching Templates...")
    r = requests.get(f"{BASE_URL}/syllabus/templates")
    templates = r.json()
    if not templates:
        print("⚠️ No templates found (Seed might be running/failed).")
    else:
        print(f"✅ Found {len(templates)} templates. Using first one: {templates[0]['name']}")
    
    # 3. Create Course
    step("Creating Course Draft...")
    course_pl = {"title": "Test Pipeline Course", "description": "Automated Test"}
    r = requests.post(f"{BASE_URL}/courses", json=course_pl)
    if r.status_code != 201:
        print(f"❌ Failed to create course: {r.text}")
        return
    course_id = r.json()['id']
    print(f"✅ Course Created: ID {course_id}")
    
    # 4. Extract Blueprint (Simulation)
    step("Extracting Blueprint...")
    sample_text = """
    Course: Test Logic 101
    Modules: 
    M1: Basics of Logic
    M2: Advanced Logic
    """
    r = requests.post(f"{BASE_URL}/syllabus/extract", json={"text": sample_text})
    if r.status_code != 200:
        print(f"❌ Extraction Failed: {r.text}")
        # Proceed with dummy blueprint
        blueprint = {"modules": [{"id": "M1", "title": "Basics"}]}
    else:
        blueprint = r.json().get('blueprint')
        print("✅ Blueprint Extracted")
        
    # 5. Update Blueprint
    step("Updating Course Blueprint...")
    r = requests.put(f"{BASE_URL}/courses/{course_id}/blueprint", json={"blueprint": blueprint})
    if r.status_code != 200:
        print(f"❌ Blueprint Update Failed: {r.text}")
        return
    print("✅ Blueprint Updated")
    
    # 6. Trigger Generation (Phase 2)
    step("Triggering Generation...")
    gen_payload = {
        "blueprint": blueprint,
        "generation_spec": {"scope": "all"},
        "prompt_text": "Generate a simple test course with 1 module.",
        "scope": {"modules": ["M1"]}
    }
    r = requests.post(f"{BASE_URL}/courses/{course_id}/generate_v2", json=gen_payload)
    if r.status_code != 200:
        print(f"❌ Generation Trigger Failed: {r.text}")
        return
    print("✅ Generation Queued")
    
    # 7. Poll for Result
    step("Polling for Completion (Max 30s)...")
    for i in range(15):
        time.sleep(2)
        r = requests.get(f"{BASE_URL}/courses/{course_id}")
        data = r.json()
        status = data.get("status")
        print(f"   Status: {status}")
        if status == "CONTENT_READY":
            print("✅ Generation Complete!")
            # print(json.dumps(data.get("content"), indent=2))
            break
        elif status == "ERROR":
            print("❌ Generation Failed (Status ERROR)")
            break
    else:
        print("⚠️ Timed out waiting for generation.")

if __name__ == "__main__":
    main()
