
import os
import json
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Mock LLM generation for speed/demo.
# In production, these would be calls to Gemini/OpenAI.

def generate_reading_material(slide_bullets: List[str]) -> str:
    """Expands bullets into reading paragraphs."""
    paragraphs = []
    for bullet in slide_bullets:
        paragraphs.append(f"Expanded concept for: '{bullet}'. This concept is fundamental to understanding the topic. Detailed explanation would go here, citing examples and relevant theories.")
    return "\n\n".join(paragraphs)

def generate_mcq_bank(topic_title: str) -> List[Dict]:
    """Generates mock MCQs."""
    return [
        {
            "question": f"What is a key concept of {topic_title}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct": "Option A",
            "explanation": "Option A is correct because..."
        },
        {
            "question": f"Which of the following applies to {topic_title}?",
            "options": ["X", "Y", "Z", "W"],
            "correct": "X",
            "explanation": "X is correct because..."
        }
    ]

def generate_mind_map(module_title: str, topics: List[str]) -> str:
    """Generates Mermaid JS Mindmap."""
    nodes = "\n    ".join([f"{t}" for t in topics])
    return f"""mindmap
  root(({module_title}))
    {nodes}
"""

def generate_case_studies(course_title: str) -> List[Dict]:
    """Generates Course-level Case Studies."""
    return [
        {"title": f"Case Study 1: {course_title} in Practice", "content": "Real-world application example..."},
        {"title": f"Case Study 2: Challenges in {course_title}", "content": "Analysis of common pitfalls..."},
        {"title": f"Case Study 3: Future of {course_title}", "content": "Emerging trends..."}
    ]

def create_course_content_bundle(course_id: int, course_title: str, approved_jobs: List[Any], output_dir: str = "data/outputs") -> str:
    """
    Generates the full eContent bundle.
    approved_jobs: List of TopicGenerationJob objects (SQLAlchemy models)
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"course_{course_id}_content_{timestamp}"
    base_path = Path(output_dir) / bundle_name
    
    # 1. Structure Creation
    # Structure:
    # /modules
    #   /module_1
    #     /topic_1
    #       reading_material.md
    #       slides.json
    #       mcq.json
    #     mind_map.md (mermaid)
    # /case_studies
    # /self_study
    
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    modules_dir = base_path / "modules"
    modules_dir.mkdir()
    
    case_studies_dir = base_path / "case_studies"
    case_studies_dir.mkdir()
    
    # Organize jobs by module
    jobs_by_module = {}
    for job in approved_jobs:
        mod_id = job.module_id or "unknown_module"
        if mod_id not in jobs_by_module:
            jobs_by_module[mod_id] = []
        jobs_by_module[mod_id].append(job)
        
    manifest = {
        "course_id": course_id,
        "course_title": course_title,
        "generated_at": timestamp,
        "modules": []
    }
    
    # 2. Generate Content per Module/Topic
    for mod_id, jobs in jobs_by_module.items():
        # Mock module title since we only have ID on job usually, 
        # unless we fetch from blueprint. Using ID for now.
        mod_dir = modules_dir / mod_id
        mod_dir.mkdir()
        
        topic_titles = []
        
        for job in jobs:
            topic_id = job.topic_id
            slides_data = job.slides_json or {}
            slides = slides_data.get("slides", [])
            
            # Helper to get title
            t_title = slides[0].get("title", topic_id) if slides else topic_id
            topic_titles.append(t_title)
            
            # Topic Dir
            t_dir = mod_dir / topic_id
            t_dir.mkdir()
            
            # A. Reading Material
            all_bullets = []
            for s in slides:
                if "bullets" in s:
                    if isinstance(s["bullets"], list):
                        all_bullets.extend(s["bullets"])
                    elif isinstance(s["bullets"], str):
                        all_bullets.append(s["bullets"])
            
            reading_text = f"# {t_title}\n\n" + generate_reading_material(all_bullets)
            (t_dir / "reading_material.md").write_text(reading_text)
            
            # B. Slides JSON (Raw)
            (t_dir / "slides.json").write_text(json.dumps(slides_data, indent=2))
            
            # C. MCQ Bank
            mcqs = generate_mcq_bank(t_title)
            (t_dir / "mcq_bank.json").write_text(json.dumps(mcqs, indent=2))
            
            # D. Web Resources
            web_resources = [
                {"title": f"Deep dive into {t_title}", "url": "https://example.com/resource1"},
                {"title": f"Video tutorial: {t_title}", "url": "https://example.com/video1"}
            ]
            (t_dir / "web_resources.json").write_text(json.dumps(web_resources, indent=2))

        # E. Module Mind Map
        mm = generate_mind_map(mod_id, topic_titles)
        (mod_dir / "mind_map.mmd").write_text(mm)
        
        # F. Discussion Topics
        discussions = [
            f"Discuss the impact of {t} on modern industry." for t in topic_titles[:2]
        ]
        (mod_dir / "discussion_topics.txt").write_text("\n".join(discussions))
        
        manifest["modules"].append({
            "id": mod_id,
            "topic_count": len(jobs),
            "artifacts": ["mind_map.mmd", "discussion_topics.txt"]
        })

    # 3. Course Level Artifacts
    case_studies = generate_case_studies(course_title)
    (case_studies_dir / "case_studies.json").write_text(json.dumps(case_studies, indent=2))
    
    self_study_text = f"# Self Study Pack for {course_title}\n\n## FAQs\n1. How do I start?\n   Refer to Module 1.\n\n## Misconceptions\n- It is not magic."
    (base_path / "self_study_pack.md").write_text(self_study_text)
    
    # 4. Write Manifest
    (base_path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    
    # 5. Zip It
    zip_path = Path(output_dir) / f"{bundle_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(base_path)
                zipf.write(file_path, arcname)
    
    # Cleanup raw folder? Maybe keep for debug. Keeping for now.
    
    return str(zip_path)
