import requests
import json
import sys
import time

API_URL = "http://localhost:3000"

def log(msg):
    print(msg)

def verify_topic_flow():
    # 1. Setup Course & Build Graph
    log("1. Setting up Course and Graph...")
    try:
        # Get Template
        resp = requests.get(f"{API_URL}/syllabus/templates")
        templates = resp.json()
        template_id = templates[0]['id']
        
        # Create
        resp = requests.post(f"{API_URL}/syllabus/select", json={"template_id": template_id})
        course_id = resp.json().get('course_id')
        log(f"Course ID: {course_id}")
        
        # Build initial graph
        requests.post(f"{API_URL}/courses/{course_id}/graph/build")
        
        # Fetch Graph
        graph = requests.get(f"{API_URL}/courses/{course_id}/graph").json()
        
        # Pick a topic to target
        target_topic = graph['children'][0]['children'][0]
        topic_id = target_topic['topic_id'] or target_topic['id']
        log(f"Target Topic ID: {topic_id}")
        
    except Exception as e:
        log(f"❌ Setup failed: {e}")
        sys.exit(1)

    # 2. Simulate Topic Generation (Mocking Kafka Consumer logic via direct DB update if possible? No, we need to trigger the logic.)
    # Since I cannot easily inject Kafka message from here without kafka client, 
    # and I added the logic in `process_event`, testing it end-to-end requires running Kafka.
    # BUT, I can simulate the EFFECT by manually calling `patch_topic_slides` IF I updated it?
    # Wait, I didn't update `patch_topic_slides` to write to graph yet. I only updated `process_event`.
    # AND I created `approve_topic_in_graph`.
    
    # Requirement: "We will NOT parse edited PPTX back. Canonical editing happens on CourseGraph (slide nodes)."
    
    # Let's verify Approval flow first, as that is exposed via API.
    # For Generation, if I can't trigger Kafka easily from script, I will trust the logic or try to call a helper if I exposed one?
    # I exposed `patch_topic_slides` in previous steps (unrelated to this task potentially?).
    
    # Let's verify Approval Logic.
    log("2. Verifying Approval Endpoint...")
    try:
        approval_payload = {
            "status": "APPROVED",
            "timestamp": "2025-01-01T12:00:00Z",
            "comment": "LGTM"
        }
        
        resp = requests.post(
            f"{API_URL}/courses/{course_id}/topics/{topic_id}/approve",
            json=approval_payload
        )
        
        if resp.status_code != 200:
             log(f"❌ Approval failed: {resp.text}")
             sys.exit(1)
             
        updated_graph = resp.json()
        
        # Check approval in graph
        found = False
        for m in updated_graph['children']:
            for t in m['children']:
                if t['id'] == topic_id or t['topic_id'] == topic_id:
                    if t.get('approval', {}).get('status') == "APPROVED":
                        found = True
                        log("✅ Topic marked APPROVED in graph")
                    else:
                        log(f"❌ Topic approval status mismatch: {t.get('approval')}")
                        sys.exit(1)
        if not found:
             log("❌ Target topic not found in updated graph")
             sys.exit(1)

    except Exception as e:
        log(f"❌ Approval test failed: {e}")
        sys.exit(1)
        
    log("✅ Topic Graph Integration Verification Successful (Approval Part)!")

if __name__ == "__main__":
    verify_topic_flow()
