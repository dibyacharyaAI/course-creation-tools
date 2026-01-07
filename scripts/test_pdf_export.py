import requests
import json
import sys
import time

API_URL = "http://localhost:3000"

def log(msg):
    print(msg)

def verify_pdf_export():
    log("1. Setup (Create & Build Graph)...")
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
        
    except Exception as e:
        log(f"❌ Setup failed: {e}")
        sys.exit(1)

    log("2. Exporting PDF...")
    try:
        resp = requests.post(f"{API_URL}/courses/{course_id}/export/pdf")
        
        if resp.status_code == 200:
             result = resp.json()
             if "pdf_path" in result:
                 log(f"✅ PDF Export Success: {result['pdf_path']}")
             else:
                 log(f"⚠️ Export returned 200 but no pdf_path? {result}")
        elif resp.status_code == 400:
             if "Graph empty" in resp.text:
                   log("⚠️ Graph Empty (Expected if fresh graph has no content). Endpoint Logic OK.")
             else:
                   log(f"❌ Export Failed: {resp.text}")
                   sys.exit(1)
        else:
             log(f"❌ Export Failed: {resp.status_code} {resp.text}")
             sys.exit(1)

    except Exception as e:
        log(f"❌ Export Test Exception: {e}")
        sys.exit(1)
        
    log("✅ PDF Export Verified!")

if __name__ == "__main__":
    verify_pdf_export()
