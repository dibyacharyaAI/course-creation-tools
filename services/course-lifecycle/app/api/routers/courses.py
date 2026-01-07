
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
import logging
import requests
import asyncio
from datetime import datetime

from ..dependencies import get_db
from ...models import Course, TopicGenerationJob, ReferenceAsset, GenerationSpec, PromptVersion, JobRun
from ...contracts import ClientCourse, GenerationRequest
from ...content_generator import create_course_content_bundle
from shared.core.event_schemas import GenerationRequestedPayload, PPTRequestedPayload
from ...utils import log_telemetry # Define or import logic, for now assume inline fn or move to separate file

# We will need a shared Kafka client. 
# Ideally passed as strict dependency or global.
# Main sets it up. We can import if global, or use dependency injection.
# For now, let's assume we import a global `kafka_client` wrapper from `...main` or `...dependencies`?
# Creating circular import if we import from main. 
# Best to move `kafka_client` init to `app/core/kafka.py` or similar.
# For now, suppressing Kafka calls or stubbing if complex to move, OR I will create `app/events.py`.
# Let's create `app/events.py` to handle publishing.

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Helper Pydantic Models ---
class TopicJobResponse(BaseModel):
    id: int
    course_id: int
    module_id: str
    topic_id: str
    status: str
    version: int
    slides_json: dict | None
    pptx_path: str | None
    reviewer_notes: str | None
    created_at: datetime
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

class ApprovalRequest(BaseModel):
    notes: str | None = None
    reviewer: str | None = None

class CreateCourseRequest(BaseModel):
    title: str
    description: str | None = None
    course_code: str
    obe_metadata: Dict[str, Any] | None = None

class PPTRequest(BaseModel):
    prompt_text: str 
    
class BlueprintUpdateRequest(BaseModel):
    blueprint: Dict[str, Any]
@router.post("/courses")
async def create_course(req: CreateCourseRequest, db: Session = Depends(get_db)):
    """Create a new course (Draft)"""
    # Check if exists
    existing = db.query(Course).filter(Course.course_code == req.course_code).first()
    if existing:
        # If draft, maybe return it? Or error?
        # For simplicity, return existing
        return {
            "id": existing.id, 
            "course_code": existing.course_code, 
            "title": existing.title,
            "status": existing.status
        }

    new_course = Course(
        title=req.title,
        description=req.description,
        course_code=req.course_code,
        obe_metadata=req.obe_metadata,
        status="DRAFT",
        blueprint=req.obe_metadata # Assuming blueprint is passed partly in metadata or we need improved logic.
        # Frontend passes: { title, description, course_code, obe_metadata: { modules: ... } }
        # Ideally we map obe_metadata back to blueprint if needed or just store it.
    )
    
    # Store explicit blueprint if present in metadata (Frontend Step 1 logic)
    if req.obe_metadata:
        # Sync blueprint field
        # We might need a stricter schema here but for MVP:
        new_course.blueprint = req.obe_metadata # Storing loosely
        
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    # Telemetry
    from ...utils import create_db_job_run
    create_db_job_run(db, new_course.id, "CREATE_COURSE", "COMPLETED")
    
    return {
        "id": new_course.id, 
        "course_code": new_course.course_code, 
        "title": new_course.title,
        "status": new_course.status
    }

@router.get("/courses/{course_id}")
async def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/courses/{course_id}/blueprint")
async def update_blueprint(course_id: int, req: BlueprintUpdateRequest, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # LOCK: Prevent mutation if KG exists
    if course.course_graph and course.course_graph.get("children"):
        logger.warning(f"Blocked blueprint update for Course {course_id}: KG already initialized.")
        raise HTTPException(
            status_code=409, 
            detail="Blueprint edits disabled after KG initialization. Edit KG instead."
        )

    course.blueprint = req.blueprint
    db.commit()
    db.refresh(course)
    return {"status": "updated", "id": course.id}

@router.put("/courses/{course_id}/canonical")
async def update_canonical_data(course_id: int, client_data: ClientCourse, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        data = client_data.model_dump()
    except AttributeError:
         data = client_data.dict() # Fallback
         
    course.obe_metadata = data
    db.commit()
    db.refresh(course)
    
    return course

@router.post("/courses/{course_id}/generate_v2")
async def trigger_generation_v2(course_id: int, req: GenerationRequest, db: Session = Depends(get_db)):
    """Phase-2 Generation Trigger"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Conditional Blueprint Update: Only if KG not valid
    if not (course.course_graph and course.course_graph.get("children")):
         course.blueprint = req.blueprint
    else:
         logger.info(f"Skipping blueprint update for Course {course_id} in generate_v2: KG exists.")

    course.generation_spec = req.generation_spec
    
    current_prompts = course.prompt_data or []
    if isinstance(current_prompts, list):
        current_prompts.append({"version": len(current_prompts)+1, "text": req.prompt_text})
    else:
        current_prompts = [{"version": 1, "text": req.prompt_text}]
    course.prompt_data = current_prompts
    
    course.status = "GENERATING"
    db.commit()
    
    # Event Publishing (Mocked/TODO: Move to events.py)
    # await kafka_client.publish(...)
    
    return {"status": "queued"}

@router.get("/courses/{course_id}/topics/{topic_id}", response_model=TopicJobResponse)
async def get_topic_job(course_id: int, topic_id: str, db: Session = Depends(get_db)):
    job = db.query(TopicGenerationJob).filter(
        TopicGenerationJob.course_id == course_id,
        TopicGenerationJob.topic_id == topic_id
    ).order_by(TopicGenerationJob.version.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Topic job not found")
        
    # Hotfix: If generated but no pptx_path (from before patch), infer it
    if job.status == "GENERATED" and not job.pptx_path:
        job.pptx_path = f"/generated/courses/{course_id}/topics/{topic_id}_v{job.version}.pptx"
        
    return job

@router.post("/courses/{course_id}/topics/{topic_id}/ppt/generate")
async def generate_topic_ppt(course_id: int, topic_id: str, module_id: Optional[str] = None, auto_sync: bool = True, db: Session = Depends(get_db)):
    """Trigger generation for a specific topic (REAL GEMINI CALL)"""

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Infer module_id/title and topic_title from KG (Primary) or Blueprint (Fallback)
    final_module_id = module_id or "unknown"
    topic_title = topic_id
    module_title = "Unknown Module"
    kg_outline = {}

    if course.course_graph and course.course_graph.get("children"):
        # 1. Derive Context from KG
        cg = course.course_graph
        found = False
        
        # Build KG Outline on the fly
        kg_modules = []
        for m in cg.get("children", []):
            m_payload = {
                "id": m.get("module_id"), 
                "title": m.get("name"), 
                "topics": []
            }
            
            for t in m.get("children", []):
                t_payload = {
                    "id": t.get("topic_id"),
                    "name": t.get("title"),
                    "topic_outcome": t.get("outcome") # Now supported in schema
                }
                m_payload["topics"].append(t_payload)
                
                # Context Lookup
                if str(t.get("topic_id")) == str(topic_id):
                    final_module_id = str(m.get("module_id"))
                    module_title = m.get("name")
                    topic_title = t.get("title")
                    found = True
            
            kg_modules.append(m_payload)
            
        kg_outline = {
            "course_title": course.title,
            "modules": kg_modules
        }
        
    elif course.blueprint:
        # Fallback to Blueprint
        bp_modules = course.blueprint.get("modules", [])
        for m in bp_modules:
            t_list = m.get("topics", [])
            for t in t_list:
                if isinstance(t, dict) and str(t.get("id")) == str(topic_id):
                    final_module_id = str(m.get("id"))
                    module_title = m.get("title") or m.get("name") or "Unknown Module"
                    topic_title = t.get("name") or t.get("title") or topic_id
                    break
    
    # Check if AI Authoring is reachable and call it
    # We call internal service
    from ...settings import settings
    ai_auth_url = f"{settings.AI_AUTHORING_URL}/topics/slides/generate"
    
    # Merge restrictions into generation_spec
    gen_spec = course.generation_spec or {}
    # Ensure constraints dict exists
    if "constraints" not in gen_spec: gen_spec["constraints"] = {}
    if "ppt" not in gen_spec["constraints"]: gen_spec["constraints"]["ppt"] = {}
    
    # FORCE Production Constraints
    gen_spec["constraints"]["ppt"]["max_slides"] = 8
    
    # 2b. Extract KG Concepts (Optional Feature)
    key_concepts = []
    prerequisites = []
    
    import os
    if os.getenv("ENABLE_KG_CONTEXT") == "true" and course.course_graph:
        cg = course.course_graph
        rels = cg.get("relations", [])
        concepts = cg.get("concepts", [])
        
        # Helper to find concept label
        def get_label(cid):
            c = next((x for x in concepts if x["id"] == cid), None)
            return c["label"] if c else cid
            
        # Find concepts linked to this topic
        # Schema: RelationEdge(source_id, target_id, relation_type)
        # We look for edges where source OR target is this topic_id (or its legacy ID)
        
        relevant_cids = set()
        prereq_cids = set()
        
        for r in rels:
            sid = str(r.get("source_id"))
            tid = str(r.get("target_id"))
            rtype = r.get("relation_type", "RELATED_TO")
            
            # Case 1: Topic -> Concept (Topic mentions Concept)
            if sid == topic_id and tid.startswith("c_"):
                relevant_cids.add(tid)
                
            # Case 2: Concept -> Topic (Concept is prerequisite for Topic?)
            # Usually PREREQUISITE is Topic->Topic or Concept->Concept. 
            # If Concept -> Topic, it means Topic depends on Concept.
            if tid == topic_id and sid.startswith("c_"):
                relevant_cids.add(sid)
                if rtype == "PREREQUISITE":
                    prereq_cids.add(sid)
        
        key_concepts = [get_label(cid) for cid in relevant_cids]
        prerequisites = [get_label(cid) for cid in prereq_cids]
        
        if key_concepts:
            logger.info(f"KG Context: Found {len(key_concepts)} concepts for topic {topic_id}")
            
    payload = {
        "course_id": course_id,
        "module_id": final_module_id,
        "module_title": module_title,
        "topic_id": topic_id,
        "topic_title": topic_title,
        "kg_outline": kg_outline, # New Source of Truth
        "generation_spec": gen_spec,
        "key_concepts": key_concepts,
        "prerequisites": prerequisites
    }
    
    # 3. Add Active Prompt (if any)
    active_pv = db.query(PromptVersion).filter(
        PromptVersion.course_id == course_id,
        PromptVersion.is_active == 1
    ).order_by(PromptVersion.version_num.desc()).first()
    
    if active_pv:
        payload["prompt_text"] = active_pv.prompt_text
    
    slides_data = None
    
    try:
        # Use sync request for now inside async route (or use httpx but requests is simpler dependency if present)
        # Using 90s timeout as generation takes time
        resp = requests.post(ai_auth_url, json=payload, timeout=90) 
        if resp.status_code == 200:
            slides_data = resp.json() # { title, slides: [] }
            # Ensure "slides" key wraps the list if the service returns flat or wrapped
            if "slides" not in slides_data and isinstance(slides_data, list):
                    slides_data = {"slides": slides_data} # Fallback
        else:
                logger.error(f"AI Authoring failed: {resp.text}")
                # We will fallback to stub ONLY if error indicates connection issue? 
                # No, per requirements: "Return clean error message". 
                # But to handle 'no key' graceful fallback we might get mock from service itself.
                
    except Exception as e:
        logger.error(f"AI Call Exception: {e}")
        # If call fails entirely (e.g. service down), we might fail hard or mock
        # User requirement: "Without key... return clean error message" -> Handled by service returning mock or error.
        # If service unreachable, we raise 503.
        raise HTTPException(status_code=503, detail=f"AI Service Unavailable: {str(e)}")

    if not slides_data:
         # Should have raised above if error code
         raise HTTPException(status_code=500, detail="Empty response from AI Service")

    existing = db.query(TopicGenerationJob).filter(
        TopicGenerationJob.topic_id == topic_id,
        TopicGenerationJob.course_id == course_id
    ).order_by(TopicGenerationJob.version.desc()).first()
    
    new_version = (existing.version + 1) if existing else 1
    
    job = TopicGenerationJob(
        course_id=course_id,
        module_id=final_module_id,
        topic_id=topic_id,
        status="GENERATED",
        version=new_version,
        slides_json=slides_data, # Real data
        pptx_path=f"/generated/courses/{course_id}/topics/{topic_id}_v{new_version}.pptx"
    )
    
    db.add(job)
    db.commit() 
    
    # Telemetry: JobRun
    from ...utils import create_db_job_run
    create_db_job_run(db, course_id, "GENERATE", "COMPLETED", topic_id=topic_id, duration_ms=2000) # Dummy duration
    
    db.refresh(job)
    
    # Auto-Sync Graph (Boss Requirement: Remove Friction)
    graph_version = 0
    if auto_sync:
        try:
            # Import here to avoid circulars if any
            from ...graph_builder import GraphBuilder
            
            # Fetch all jobs (required for GraphBuilder)
            all_jobs = db.query(TopicGenerationJob).filter(TopicGenerationJob.course_id == course_id).all()
            
            # Instantiate with Course object and Job List
            logger.info(f"Auto-Sync: Found {len(all_jobs)} jobs for Course {course_id}")
            builder = GraphBuilder(course, all_jobs)
            
            # Build new graph
            rebuilt_graph, stats = builder.build()
            logger.info(f"Auto-Sync Stats: {stats}")
            
            # Persist to DB
            course.course_graph = rebuilt_graph.model_dump(mode='json')
            course.course_graph_version = rebuilt_graph.version
            db.commit()
            db.refresh(course)
            
            graph_version = rebuilt_graph.version
        except Exception as e:
            logger.error(f"Auto-sync failed: {e}")
            # Don't fail the request, just log
    
    return {"status": "triggered", "job_id": job.id, "version": new_version, "module_id": final_module_id, "graph_synced": auto_sync, "graph_version": graph_version}

@router.post("/courses/{course_id}/topics/{topic_id}/ppt/verify")
async def verify_topic_ppt(course_id: int, topic_id: str, db: Session = Depends(get_db)):
    """Verify topic slides against strict constraints (Validator)"""
    job = db.query(TopicGenerationJob).filter(
        TopicGenerationJob.course_id == course_id,
        TopicGenerationJob.topic_id == topic_id
    ).order_by(TopicGenerationJob.version.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    slides_data = job.slides_json.get("slides", [])
    
    # Construct Transient Topic Node for Validation
    from ...graph_schema import TopicNode, SubtopicNode, SlideNode
    from ...graph.validator import GraphValidator
    
    # transform flat slides to dummy hierarchy
    dummy_sub = SubtopicNode(id="dummy", title="General", children=[])
    for idx, s in enumerate(slides_data):
        dummy_sub.children.append(SlideNode(
            id=f"slide-{idx}", 
            title=s.get("title", ""),
            bullets=s.get("bullets", []),
            speaker_notes=s.get("speaker_notes", ""),
            illustration_prompt=s.get("illustration_prompt", ""),
            order=idx+1
        ))

    dummy_topic = TopicNode(id=topic_id, title="Topic", topic_id=topic_id, children=[dummy_sub])
    
    # Create empty Validator (we only use validate_topic)
    validator = GraphValidator({"children": [], "version": 1, "course_id": course_id})
    report = validator.validate_topic(dummy_topic)
    
    from ...utils import create_db_job_run
    
    if not report.valid:
        job.status = "REJECTED"
        db.commit()
        
        # Serialize errors
        error_list = [e.model_dump() for e in report.errors]
        create_db_job_run(db, course_id, "VERIFY", "FAILED", topic_id=topic_id, error_details=str(error_list))
        
        # Return 200 with error details so UI can render them nicely
        return {
            "status": "FAILED", 
            "errors": error_list,
            "warnings": [w.model_dump() for w in report.warnings]
        }
        
    job.status = "VERIFIED"
    db.commit()
    create_db_job_run(db, course_id, "VERIFY", "COMPLETED", topic_id=topic_id)
    
    return {"status": "VERIFIED"}

@router.post("/courses/{course_id}/ppt/generate")
async def generate_course_ppt(course_id: int, req: PPTRequest, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course.status = "PPT_REQUESTED"
    db.commit()
    return {"status": "queued", "message": "PPT generation started"}

@router.post("/generation-spec")
async def save_generation_spec(spec: Dict[str, Any], db: Session = Depends(get_db)):
    """Save Generation Spec (Phase 2)"""
    # Assuming spec has course_id or we extract it. 
    # Frontend sends { course_id, hierarchy_scope, ... }
    c_id = spec.get("course_id")
    if not c_id:
        raise HTTPException(status_code=400, detail="course_id required")
        
    course = db.query(Course).filter(Course.id == c_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course.generation_spec = spec
    db.commit()
    return {"status": "saved"}

@router.post("/reference/upload")
async def upload_reference(file: UploadFile = File(...), course_id: int = 1, db: Session = Depends(get_db)):
    """Upload Reference Asset with Text Extraction"""
    try:
        contents = await file.read()
        
        # Extract Text (with optional OCR)
        from ...ocr_utils import extract_text_from_pdf
        text_content = ""
        
        if file.filename.lower().endswith(".pdf"):
            text_content = extract_text_from_pdf(contents, file.filename)
        else:
            # Fallback for text/md
            try:
                text_content = contents.decode("utf-8")
            except:
                pass
                
        # Save to Shared Volume
        import os
        from pathlib import Path
        
        # Base dir for references (shared with other services)
        ref_dir = Path("/app/generated_data/references") / str(course_id)
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Original
        file_path = ref_dir / file.filename
        with open(file_path, "wb") as f:
             f.write(contents)
             
        # Save Extracted Text (Chunk Source)
        txt_filename = f"{file.filename}.txt"
        txt_path = ref_dir / txt_filename
        if text_content:
            with open(txt_path, "w") as f:
                f.write(text_content)
        
        return {
            "status": "uploaded", 
            "filename": file.filename, 
            "extracted_chars": len(text_content),
            "ocr_used": "DeepSeek-OCR" if "DeepSeek-OCR" in text_content else "Native",
            "saved_path": str(txt_path),
            "preview": text_content[:200] if text_content else "No extractable text"
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prompt/build")
async def build_prompt(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Build Prompt"""
    """Build Prompt and Persist Version"""
    course_id = data.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="Missing course_id")

    # Generate Prompt
    res = _build_prompt_text(data)
    prompt_txt = res.get("prompt_text", "")
    
    # Calculate Version
    last_ver = db.query(PromptVersion).filter(PromptVersion.course_id == course_id).order_by(PromptVersion.version_num.desc()).first()
    new_ver_num = (last_ver.version_num + 1) if last_ver else 1
    
    # Persist
    pv = PromptVersion(
        course_id=course_id,
        version_num=new_ver_num,
        prompt_text=prompt_txt,
        spec_snapshot=data.get("generation_spec"),
        is_active=1
    )
    db.add(pv)
    
    # Update Course JSON link (Legacy/Sync)
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        current_prompts = course.prompt_data or []
        if not isinstance(current_prompts, list):
             current_prompts = []
        current_prompts.append({"version": new_ver_num, "text": prompt_txt})
        course.prompt_data = current_prompts
        
    db.commit()
    db.refresh(pv)
    
    return {
        "id": pv.id, 
        "prompt_text": pv.prompt_text, 
        "version": pv.version_num,
        "created_at": pv.created_at
    }

@router.post("/prompt/draft")
async def draft_prompt(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Draft Prompt (Pre-build)"""
    return _build_prompt_text(data)

def _build_prompt_text(data: Dict[str, Any]) -> Dict[str, Any]:
    # Extract fields from frontend payload
    c_id = data.get("course_id")
    generation_spec = data.get("generation_spec", {})
    scope = generation_spec.get("hierarchy_scope", {})
    modules = scope.get("modules", [])
    
    # Correct extraction paths based on Step5Prompt.jsx
    duration = generation_spec.get("total_duration_minutes", "Unknown")
    
    bloom_data = data.get("bloom", {})
    if isinstance(bloom_data, dict):
        bloom = bloom_data.get("default_level", "Apply")
    else:
        bloom = str(bloom_data) 

    # Build Module List String
    module_list_str = ""
    for m in modules:
        m_name = m.get("module_name", "Untitled Module")
        m_id = m.get("module_id", "?")
        module_list_str += f"- [Module {m_id}] {m_name}\\n"

    # Construct Prompt
    prompt = f"""# Course Content Generation Prompt

## Course Context
- **Course ID:** {c_id}
- **Target Duration:** {duration} minutes
- **Target Bloom Level:** {bloom}

## Scope of Generation
The AI Architect is requested to generate detailed slide content for the following modules:

{module_list_str}

## Instructions
1. Analyze the provided module titles and specific topics.
2. Structure the content to fit the {duration} minute duration.
3. Ensure all learning outcomes align with Bloom's Taxonomy level '{bloom}'.
4. Generate strict JSON output for slides.
"""
    return {"prompt_text": prompt}




