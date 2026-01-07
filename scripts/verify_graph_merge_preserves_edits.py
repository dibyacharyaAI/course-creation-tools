import requests
import json
import time
import sys

API_URL = "http://localhost:3000/api/lifecycle"

def check(response, condition, msg):
    if condition:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        print(f"Response: {response.text}")
        sys.exit(1)

def run():
    print("========================================")
    print("    VERIFYING SAFETY & RELIABILITY")
    print("========================================")

    # 1. Create Course
    print("[1] Creating Course...")
    c_res = requests.post(f"{API_URL}/courses", json={
        "title": "Security Testing Course", 
        "topic": "Security Testing",
        "course_code": "SEC101"
    })
    check(c_res, c_res.status_code == 200, "Course Created")
    cid = c_res.json()["id"]
    print(f"    -> Course ID: {cid}")

    print(f"    -> Course ID: {cid}")

    # 1b. Wait for Async Blueprint (if any)
    print("    -> Waiting 10s for blueprint...")
    time.sleep(10)

    # 2. Build Graph
    print("[2] Building Initial Graph...")
    requests.post(f"{API_URL}/courses/{cid}/graph/build")
    
    # 3. Simulate Topic Generation (Mock External to avoid cost/time if possible, but we use real flow for integration)
    # We need a topic ID.
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph = g_res.json()
    if not graph["children"]:
        print("❌ Graph empty. Blueprint failed?")
        sys.exit(1)
    
    # Pick first topic
    module = graph["children"][0]
    topic = module["children"][0]
    tid = topic["topic_id"] or topic["id"]
    print(f"    -> Target Topic: {tid}")

    # Trigger Generation
    print("[3] Generating Topic (v1)...")
    gen_res = requests.post(f"{API_URL}/courses/{cid}/topics/{tid}/ppt/generate?auto_sync=true")
    check(gen_res, gen_res.status_code == 200, "Generation Triggered")
    
    # Wait for completion (poll)
    print("    -> Waiting for generation...")
    for _ in range(20):
        time.sleep(2)
        j_res = requests.get(f"{API_URL}/courses/{cid}/topics/{tid}")
        if j_res.json()["status"] == "GENERATED":
            break
    else:
        print("❌ Timeout waiting for generation")
        sys.exit(1)
        
    # Get Graph State v1
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph_v1 = g_res.json()
    slides_v1 = []
    # Find slides
    for m in graph_v1["children"]:
         for t in m["children"]:
             if t["id"] == topic["id"] or t["topic_id"] == tid:
                 for sub in t["children"]:
                     slides_v1.extend(sub["children"])
    
    print(f"    -> Generated {len(slides_v1)} slides.")
    if not slides_v1:
        print("❌ No slides found.")
        sys.exit(1)
        
    slide_to_edit = slides_v1[0]
    sid = slide_to_edit["id"]

    # 4. Edit a Slide (Set edited_by_user)
    print(f"[4] Editing Slide {sid}...")
    patch_res = requests.patch(f"{API_URL}/courses/{cid}/topics/{tid}/slides/{sid}", json={
        "title": "EDITED BY USER",
        "bullets": ["User content preserved"]
    })
    check(patch_res, patch_res.status_code == 200, "Slide Patched")

    # 5. Regenerate Topic (v2)
    print("[5] Regenerating Topic (v2)...")
    gen_res = requests.post(f"{API_URL}/courses/{cid}/topics/{tid}/ppt/generate?auto_sync=true")
    check(gen_res, gen_res.status_code == 200, "Regeneration Triggered")
    
    # Wait
    print("    -> Waiting for regeneration...")
    time.sleep(5) # Give it a moment to mock/process
    # Wait loop
    for _ in range(20):
        time.sleep(2)
        j_res = requests.get(f"{API_URL}/courses/{cid}/topics/{tid}")
        if j_res.json()["version"] > 1: # Assuming version incremented
             break
    
    # Check Graph Again
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph_v2 = g_res.json()
    slides_v2 = []
    for m in graph_v2["children"]:
         for t in m["children"]:
             if t["id"] == topic["id"]:
                 for sub in t["children"]:
                     slides_v2.extend(sub["children"])
                     
    # Locate edited slide
    target = next((s for s in slides_v2 if s["id"] == sid), None)
    if not target:
        print("❌ Edited slide ID lost!")
        sys.exit(1)
        
    print(f"    -> Slide Title after Regen: {target['title']}")
    if target["title"] == "EDITED BY USER":
        print("✅ User Edit Preserved!")
    else:
        print("❌ User Edit OVERWRITTEN!")
        sys.exit(1)

    # 6. Test Optimistic Locking
    print("[6] Testing Optimistic Locking...")
    current_ver = graph_v2["version"]
    print(f"    -> Current Version: {current_ver}")
    
    # Try updating with OLD version
    graph_v2["version"] = current_ver - 1
    conflict_res = requests.patch(f"{API_URL}/courses/{cid}/graph", json=graph_v2)
    
    if conflict_res.status_code == 409:
        print("✅ Optimistic Locking Worked (Got 409)")
    else:
        print(f"❌ Optimistic Locking Failed (Got {conflict_res.status_code})")
        sys.exit(1)

    print("========================================")
    print("    VERIFICATION PASSED 🚀")
    print("========================================")

if __name__ == "__main__":
    run()
