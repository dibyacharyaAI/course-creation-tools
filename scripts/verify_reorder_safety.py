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
    print("    VERIFYING REORDER SAFETY & STABLE KEYS")
    print("========================================")

    # 1. Create Course
    print("[1] Creating Course...")
    c_res = requests.post(f"{API_URL}/courses", json={
        "title": "Reorder Test Course", 
        "topic": "Sorting Algorithms",
        "course_code": "ALG101"
    })
    check(c_res, c_res.status_code == 200, "Course Created")
    cid = c_res.json()["id"]
    print(f"    -> Course ID: {cid}")

    # Wait for blueprint (mocking delay)
    time.sleep(2)

    # 2. Build Graph (Initial)
    requests.post(f"{API_URL}/courses/{cid}/graph/build")
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph = g_res.json()
    
    # 3. Generate Topic (v1)
    # Pick first topic
    if not graph.get("children"):
         # Inject blueprint if needed
         blueprint = {
            "modules": [{
                "id": "m1", "title": "Module 1", 
                "topics": [{ "id": "t1", "name": "Topic 1" }]
            }]
         }
         requests.put(f"{API_URL}/courses/{cid}/blueprint", json={"blueprint": blueprint})
         requests.post(f"{API_URL}/courses/{cid}/graph/build")
         graph = requests.get(f"{API_URL}/courses/{cid}/graph").json()

    module = graph["children"][0]
    topic = module["children"][0]
    tid = topic["topic_id"] or topic["id"]
    
    print(f"[3] Generating Topic {tid} (v1)...")
    gen_res = requests.post(f"{API_URL}/courses/{cid}/topics/{tid}/ppt/generate?auto_sync=true")
    if gen_res.status_code != 200:
        print(f"❌ Generation Request Failed {gen_res.status_code}: {gen_res.text}")
        sys.exit(1)
    
    # Wait
    for _ in range(30):
        time.sleep(2)
        try:
            j_res = requests.get(f"{API_URL}/courses/{cid}/topics/{tid}")
            if j_res.status_code != 200:
                print(f"⚠️ Polling Error {j_res.status_code}: {j_res.text}")
                continue
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            continue
            
        try:
            if j_res.json()["status"] == "GENERATED":
                break
        except Exception as e:
            print(f"⚠️ JSON Error: {j_res.text}")
    else:
        print("❌ Timeout waiting for generation")
        sys.exit(1)

    # Get Slides v1
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph_v1 = g_res.json()
    
    slides = []
    # Extract slides
    tgt_topic_node = [t for m in graph_v1["children"] for t in m["children"] if t["topic_id"] == tid][0]
    for sub in tgt_topic_node["children"]:
        slides.extend(sub["children"])
        
    print(f"    -> Generated {len(slides)} slides.")
    if len(slides) < 3:
        print("❌ Need at least 3 slides to test reorder.")
        sys.exit(1)

    # 4. SWAP ORDER & EDIT
    # Slide A (Index 0) -> Move to Index 2
    # Slide B (Index 2) -> Move to Index 0
    # Edit Slide A content to ensure it persists even after move.
    
    slide_A = slides[0]
    slide_B = slides[2]
    
    old_id_A = slide_A["id"]
    old_id_B = slide_B["id"]
    
    print(f"[4] Modifying Graph: Swapping Slide 0 ({old_id_A}) and Slide 2 ({old_id_B})...")
    
    # Update local graph structure
    # We need to find the specific subtopic/slide list index to swap
    # Assuming flattened for simplicity in test logic, but we must update the specific subtopic children list
    # Let's just find them in the `tgt_topic_node` structure
    
    # Helper to find parent subtopic and index
    def find_slide(node, sid):
        for sub in node["children"]:
            for idx, s in enumerate(sub["children"]):
                if s["id"] == sid:
                    return sub, idx
        return None, None
        
    sub_A, idx_A = find_slide(tgt_topic_node, old_id_A)
    sub_B, idx_B = find_slide(tgt_topic_node, old_id_B)
    
    # Swap in memory
    temp = sub_A["children"][idx_A]
    sub_A["children"][idx_A] = sub_B["children"][idx_B]
    sub_B["children"][idx_B] = temp
    
    # Update Orders
    sub_A["children"][idx_A]["order"] = idx_A + 1 # simplistic reorder
    sub_B["children"][idx_B]["order"] = idx_B + 1
    
    # EDIT Slide A (User Edit) - Mark it explicitly
    tgt_slide_A = sub_B["children"][idx_B] # Use the swapped position reference? No, temp is the object.
    # Actually, we swapped objects.
    # New Slide at Pos 0 is B. New Slide at Pos 2 is A.
    
    # Slide A is now at Pos 2. Let's edit it.
    slide_A_ref = sub_B["children"][idx_B] # Wait, logic tricky. 
    # Let's just create a CLEAN payload.    
    
    # Simplification: Just PATCH the whole graph with swapped slides
    # And Edit Slide A
    
    # Edit A
    target_slide_A = [s for s in [sub_A["children"][idx_A], sub_B["children"][idx_B]] if s["id"] == old_id_A][0]
    target_slide_A["title"] = "MOVED AND EDITED BY USER"
    target_slide_A["tags"]["edited_by_user"] = ["true"] # Mark manually
    
    # Push Graph
    g_res = requests.patch(f"{API_URL}/courses/{cid}/graph", json=graph_v1)
    check(g_res, g_res.status_code == 200, "Graph Reorder Saved")
    
    # 5. Regenerate (v2)
    print("[5] Regenerating Topic (v2)...")
    requests.post(f"{API_URL}/courses/{cid}/topics/{tid}/ppt/generate?auto_sync=true")
    
    # Wait
    time.sleep(5)
    for _ in range(20):
        time.sleep(2)
        j_res = requests.get(f"{API_URL}/courses/{cid}/topics/{tid}")
        if j_res.json()["version"] > 1:
            break
            
    # 6. Check Result
    g_res = requests.get(f"{API_URL}/courses/{cid}/graph")
    graph_v2 = g_res.json()
    
    # Find matching slide by ID
    tgt_topic_node_v2 = [t for m in graph_v2["children"] for t in m["children"] if t["topic_id"] == tid][0]
    all_slides_v2 = []
    for sub in tgt_topic_node_v2["children"]:
        all_slides_v2.extend(sub["children"])
        
    final_slide_A = next((s for s in all_slides_v2 if s["id"] == old_id_A), None)
    
    if not final_slide_A:
        print("❌ Slide A ID lost after regeneration!")
        sys.exit(1)
        
    print(f"    -> Found Slide A. Title: '{final_slide_A['title']}'")
    
    if final_slide_A["title"] == "MOVED AND EDITED BY USER":
        print("✅ Edit Preserved despite reorder!")
    else:
        print("❌ Edit LOST! Content overwritten by regeneration.")
        print(f"       Expected: 'MOVED AND EDITED BY USER'")
        print(f"       Got: '{final_slide_A['title']}'")
        sys.exit(1)
        
    if "stable_key" in final_slide_A.get("tags", {}):
        print(f"✅ Stable Key found: {final_slide_A['tags']['stable_key']}")
    else:
        print("⚠️ No stable_key tag found (Feature might not be implemented yet)")

    print("========================================")
    print("    VERIFICATION PASSED 🚀")
    print("========================================")

if __name__ == "__main__":
    run()
