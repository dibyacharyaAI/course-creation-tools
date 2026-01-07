import requests
import json
import sys

API_URL = "http://localhost:3000"

def log(msg):
    print(msg)

def verify():
    # 1. List Templates
    log("1. Fetching Templates...")
    try:
        resp = requests.get(f"{API_URL}/syllabus/templates")
        resp.raise_for_status()
        templates = resp.json()
        if not templates:
            log("❌ No templates found.")
            sys.exit(1)
        template_id = templates[0]['id']
        log(f"Selected Template: {template_id}")
    except Exception as e:
        log(f"❌ Failed to fetch templates: {e}")
        # Assuming templates endpoint might be under /api/lifecycle? 
        # But previous script used root. Let's assume gateway mapping /syllabus -> course-lifecycle/syllabus
        sys.exit(1)

    # 2. Create Course
    log("2. Creating Course...")
    try:
        resp = requests.post(f"{API_URL}/syllabus/select", json={"template_id": template_id})
        resp.raise_for_status()
        data = resp.json()
        course_id = data.get('course_id')
        log(f"Created Course ID: {course_id}")
    except Exception as e:
        log(f"❌ Failed to create course: {e}")
        sys.exit(1)

    # 3. Get Graph
    log("3. Fetching Graph...")
    try:
        resp = requests.get(f"{API_URL}/courses/{course_id}/graph")
        if resp.status_code == 404:
             log("❌ Endpoint /graph not found. Service might need restart.")
             sys.exit(1)
        resp.raise_for_status()
        graph = resp.json()
        log(f"Graph Version: {graph.get('version')}")
        
        if graph.get('version') != 1:
            log(f"❌ Expected version 1, got {graph.get('version')}")
            sys.exit(1)
    except Exception as e:
        log(f"❌ Failed to get graph: {e}")
        sys.exit(1)

    # 4. Patch Graph
    log("4. Patching Graph (Add Module)...")
    try:
        # Clone graph and add child
        new_graph = graph.copy()
        new_graph['children'].append({
            "name": "New Module",
            "order": 1,
            "children": []
        })
        
        resp = requests.patch(f"{API_URL}/courses/{course_id}/graph", json=new_graph)
        resp.raise_for_status()
        
        patched_graph = resp.json()
        new_version = patched_graph.get('version')
        log(f"New Version: {new_version}")
        
        if new_version != 2:
            log(f"❌ Expected version 2, got {new_version}")
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Failed to patch graph: {e}")
        sys.exit(1)

    # 5. Invalid Patch
    log("5. Testing Invalid Patch...")
    try:
        invalid_graph = {"course_id": course_id, "children": [{"order": 1}]} # Missing name
        resp = requests.patch(f"{API_URL}/courses/{course_id}/graph", json=invalid_graph)
        
        log(f"Invalid Patch Status: {resp.status_code}")
        if resp.status_code != 422:
            log(f"❌ Expected 422, got {resp.status_code}")
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Failed invalid patch test: {e}")
        sys.exit(1)

    log("✅ CourseGraph Verification Successful!")

if __name__ == "__main__":
    verify()
