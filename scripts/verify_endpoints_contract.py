import requests
import sys

BASE_URL = "http://localhost:3000/api/lifecycle"

def check_endpoint(method, path, desc):
    url = f"{BASE_URL}{path}"
    print(f"Checking {method} {path} ({desc})...", end=" ")
    try:
        # We expect 401, 404, or 422, but NOT 404 for the route itself.
        # Ideally options or just hitting it with dummy data.
        # Since we don't have a valid course ID easily, we rely on 404 "Course not found" 
        # vs 404 "Not Found" (route missing).
        # FastAPI returns {"detail": "Not Found"} for missing route.
        # Ours return {"detail": "Course not found"} if route exists but ID is bad.
        
        response = requests.request(method, url, json={}, timeout=2)
        
        if response.status_code == 404:
            try:
                msg = response.json().get("detail", "")
                if msg == "Not Found":
                    print("❌ MISSING (Route not found)")
                    return False
                else:
                    print(f"✅ FOUND (Response: {msg})")
                    return True
            except:
                print("❌ ERROR (Non-JSON 404)")
                return False
        elif response.status_code in [200, 422, 400, 401, 500]:
             print(f"✅ FOUND (Status: {response.status_code})")
             return True
        else:
            print(f"❓ UNKNOWN (Status: {response.status_code})")
            return True # Likely exists
            
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        return False

endpoints = [
    ("GET", "/courses/1/graph", "Get Graph"),
    ("POST", "/courses/1/graph/build", "Build Graph"),
    ("PATCH", "/courses/1/graph", "Update Graph"),
    ("POST", "/courses/1/topics/topic1/approve", "Approve Topic"),
    ("PATCH", "/courses/1/topics/topic1/slides/slide1", "Patch Slide"),
    ("POST", "/courses/1/export/ppt", "Export PPT"),
    ("POST", "/courses/1/export/pdf", "Export PDF"),
]

print("Verifying API Contract...")
print("-" * 50)
success = True
for method, path, desc in endpoints:
    if not check_endpoint(method, path, desc):
        success = False

print("-" * 50)
if success:
    print("ALL ROUTES VERIFIED.")
    sys.exit(0)
else:
    print("SOME ROUTES MISSING.")
    sys.exit(1)
