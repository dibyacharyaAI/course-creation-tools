
import os
import json

# Dynamically find repo root/data
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)
DATA_ROOT = os.path.join(repo_root, "data")
MANIFEST_PATH = os.path.join(DATA_ROOT, "manifest.json")
RAW_ROOT = os.path.join(DATA_ROOT, "raw/syllabus/extracted")

def scan_and_update():
    print(f"Scanning {RAW_ROOT}...")
    
    # Load existing manifest
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r') as f:
            data = json.load(f)
    else:
        data = {"templates": [], "syllabi": []}

    syllabi = data.get("syllabi", [])
    existing_ids = {s["id"] for s in syllabi}
    
    new_count = 0
    
    for root, dirs, files in os.walk(RAW_ROOT):
        for file in files:
            if file.lower().endswith(".docx") or file.lower().endswith(".pdf"):
                # Rel path from data1 root
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DATA_ROOT)
                
                name = os.path.splitext(file)[0]
                # ID generation consistent with loader
                t_id = f"raw-{name.replace(' ', '_')}"
                
                if t_id in existing_ids:
                    continue
                
                # Heuristic for course code
                parts = name.split()
                course_code = parts[-1] if len(parts) > 0 and any(c.isdigit() for c in parts[-1]) else "General"
                
                entry = {
                    "id": t_id,
                    "name": name, # Clean name
                    "file": rel_path,
                    "type": "document",
                    "course_code": course_code
                }
                syllabi.append(entry)
                existing_ids.add(t_id)
                new_count += 1
                
    data["syllabi"] = syllabi
    
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Updated manifest. Added {new_count} new entries. Total: {len(syllabi)}")

if __name__ == "__main__":
    scan_and_update()
