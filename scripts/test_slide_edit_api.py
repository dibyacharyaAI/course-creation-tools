import requests
import json
import sys
import time

API_URL = "http://localhost:3000"

def log(msg):
    print(msg)

def verify_slide_edit():
    # 1. Setup
    log("1. Setup...")
    try:
        # Get Template
        resp = requests.get(f"{API_URL}/syllabus/templates")
        templates = resp.json()
        template_id = templates[0]['id']
        
        # Create
        resp = requests.post(f"{API_URL}/syllabus/select", json={"template_id": template_id})
        course_id = resp.json().get('course_id')
        log(f"Course ID: {course_id}")
        
        # Build Graph
        requests.post(f"{API_URL}/courses/{course_id}/graph/build")
        
        # Fetch Graph
        graph = requests.get(f"{API_URL}/courses/{course_id}/graph").json()
        
        # Target a slide
        # Graph -> Module -> Topic -> Subtopic -> Slide
        target_mod = graph['children'][0]
        target_topic = target_mod['children'][0]
        if not target_topic.get('children'):
             log("❌ No content generated/found in topic. Cannot test slide edit.")
             sys.exit(1)
             
        target_sub = target_topic['children'][0]
        if not target_sub.get('children'):
             log("❌ No slides in subtopic.")
             sys.exit(1)
             
        target_slide = target_sub['children'][0]
        slide_id = target_slide['id']
        topic_id = target_topic['topic_id'] or target_topic['id']
        
        log(f"Target Slide: {slide_id} in Topic: {topic_id}")
        
    except Exception as e:
        log(f"❌ Setup failed: {e}")
        sys.exit(1)

    # 2. Edit Slide
    log("2. Editing Slide...")
    try:
        new_title = "Edited Title via Graph API"
        update_payload = {
            "title": new_title,
            "order": 99
        }
        
        resp = requests.patch(
            f"{API_URL}/courses/{course_id}/topics/{topic_id}/slides/{slide_id}",
            json=update_payload
        )
        
        if resp.status_code != 200:
            log(f"❌ Edit failed: {resp.text}")
            sys.exit(1)
            
        updated_graph = resp.json()
        new_ver = updated_graph['version']
        log(f"New Version: {new_ver}")
        
        # Verify Change
        found = False
        for m in updated_graph['children']:
            for t in m['children']:
                for sub in t['children']:
                    for s in sub['children']:
                        if s['id'] == slide_id:
                            if s['title'] == new_title and s['order'] == 99:
                                found = True
                                log("✅ Slide updated correctly in Graph")
                            else:
                                log(f"❌ Slide content mismatch: {s}")
                                sys.exit(1)
        if not found:
            log("❌ Slide not found in updated graph")
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Edit test failed: {e}")
        sys.exit(1)
        
    # 3. Invalid Constraint
    log("3. Testing Constraint (Empty Illustration)...")
    try:
        resp = requests.patch(
            f"{API_URL}/courses/{course_id}/topics/{topic_id}/slides/{slide_id}",
            json={"illustration_prompt": "   "}
        )
        if resp.status_code == 400:
            log("✅ Constraint Verified (400 Bad Request)")
        else:
            log(f"❌ Expected 400, got {resp.status_code}")
            sys.exit(1)
    except Exception as e:
        log(f"❌ Constraint test failed: {e}")
        sys.exit(1)

    log("✅ Slide Edit API Verification Successful!")

if __name__ == "__main__":
    verify_slide_edit()
