import json
import os
from typing import List, Optional
from pydantic import BaseModel

class SyllabusTemplate(BaseModel):
    template_id: str
    display_label: str
    course_code: str
    semester: Optional[str]
    branch: Optional[str]
    syllabus_path: str
    syllabus_exists: bool
    type: str = "document" # document | blueprint

class CatalogLoader:
    def __init__(self, data_pack_root: str = ""):
        # Patch for local execution
        if not data_pack_root:
             data_pack_root = "/app/data" if os.path.exists("/app/data") else "data"
        self.data_pack_root = data_pack_root
        self.manifest_path = os.path.join(data_pack_root, "manifests/syllabus_catalog_index.json")
        self._templates: List[SyllabusTemplate] = []
        self._load_catalog()

    def _load_catalog(self):
        # 1. Try Master Manifest (manifest.json)
        master_manifest = os.path.join(self.data_pack_root, "manifest.json")
        print(f"Checking for master manifest at: {master_manifest}")
        if os.path.exists(master_manifest):
            try:
                with open(master_manifest, 'r') as f:
                    data = json.load(f)
                    
                # Handle new schema: { templates: [], syllabi: [] }
                items = data.get("templates", []) + data.get("syllabi", [])
                
                for item in items:
                    self._templates.append(SyllabusTemplate(
                        template_id=item.get("id"),
                        display_label=item.get("name"),
                        course_code=item.get("course_code", "General"),
                        semester=item.get("semester"),
                        branch=item.get("program"),
                        syllabus_path=item.get("file"),
                        syllabus_exists=True,
                        type=item.get("type", "document")
                    ))
                print(f"Loaded {len(self._templates)} templates from master manifest.")
                print(f"Loaded {len(self._templates)} templates from master manifest.")
                return # Prioritize manifest and skip scanning to avoid crashes/dupes
            except Exception as e:
                print(f"Error loading master manifest: {e}")

        # 2. Scan Raw Directory (Fallback/Extension)
        raw_path = os.path.join(self.data_pack_root, "raw/syllabus/extracted")
        if os.path.exists(raw_path):
            self._scan_directory(raw_path)

    def _scan_directory(self, root_path: str):
        print(f"Scanning raw syllabi in {root_path}...")
        existing_ids = {t.template_id for t in self._templates}
        
        for root, dirs, files in os.walk(root_path):
            for file in files:
                if file.lower().endswith(".docx") or file.lower().endswith(".pdf"):
                    try:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.data_pack_root)
                        
                        # Simple heuristic for ID/Name
                        name = os.path.splitext(file)[0]
                        # Try to extract course code (e.g., "Env Engg XCT 3002")
                        # Split by space, take last part if it looks like code? 
                        parts = name.split()
                        course_code = parts[-1] if len(parts) > 0 and any(c.isdigit() for c in parts[-1]) else "General"
                        branch = os.path.basename(root) # Folder name
                        
                        # Generate ID
                        t_id = f"raw-{name.replace(' ', '_')}"
                        
                        if t_id in existing_ids:
                            continue
                        
                        template = SyllabusTemplate(
                            template_id=t_id,
                            display_label=name,
                            course_code=course_code,
                            semester=None,
                            branch=branch,
                            syllabus_path=rel_path,
                            syllabus_exists=True
                        )
                        self._templates.append(template)
                        existing_ids.add(t_id)
                    except Exception as e:
                        print(f"Skipping file {file} due to error: {e}")
        print(f"Total templates after scan: {len(self._templates)}")

    def get_templates(self) -> List[SyllabusTemplate]:
        return self._templates

    def get_template(self, template_id: str) -> Optional[SyllabusTemplate]:
        for t in self._templates:
            if t.template_id == template_id:
                return t
        return None

    def get_syllabus_absolute_path(self, template_id: str) -> Optional[str]:
        template = self.get_template(template_id)
        if not template:
            return None
        
        # syllabus_path in JSON is relative, e.g., "catalog/syllabi/..."
        # We need to prepend data_pack_root/catalog/...? 
        # Wait, the JSON path is "catalog/syllabi/..." which implies it starts inside 'data1' but let's check structure.
        # "syllabus_path": "catalog/syllabi/branch-unknown/..."
        # So full path is data_pack_root + syllabus_path
        # But data_pack_root is /app/data1. 
        # So /app/data1/catalog/syllabi/...
        
        # HOWEVER, the manifests/syllabus_catalog_index.json is in manifests/
        # Check if syllabus_path includes 'data1' prefix? No, checked file content.
        # "syllabus_path": "catalog/syllabi/branch-unknown/sem-unknown/XCT10003/syllabus/v1/syllabus.docx"
        
        full_path = os.path.join(self.data_pack_root, template.syllabus_path)
        if os.path.exists(full_path):
            return full_path
        return None
