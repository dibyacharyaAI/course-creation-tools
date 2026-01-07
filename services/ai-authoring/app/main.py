import asyncio
import os
import json
from fastapi import FastAPI, HTTPException
from shared.core.settings import BaseAppSettings
from shared.core.logging import setup_logging
from shared.clients.kafka_client import KafkaClient
from shared.core.event_schemas import ContentGeneratedPayload, PPTGeneratedPayload, ContentReadyForIndexingPayload
from rag.gemini_client import GeminiClient
from pydantic import BaseModel
from .generators.ppt_generator import PptGenerator
from .generators.content_expander import ContentExpander
from .prompt_builder import PromptBuilder



class Settings(BaseAppSettings):
    APP_NAME: str = "AI Authoring Service"

settings = Settings()
logger = setup_logging(settings.APP_NAME)

# Validate API key on startup
# Validate API key on startup
if not settings.GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY is not set! AI features will fail.")
else:
    logger.info(f"✅ GEMINI_API_KEY loaded successfully")

# Kafka Setup
kafka_client = KafkaClient(settings.KAFKA_BOOTSTRAP_SERVERS, settings.APP_NAME)

# Initialize Gemini client with configured models
gemini_client = GeminiClient(
    api_key=settings.GEMINI_API_KEY or "",
    primary_model=settings.PRIMARY_LLM_MODEL,
    fallback_model=settings.FALLBACK_LLM_MODEL,
    enable_fallback=settings.ENABLE_LLM_FALLBACK
)

ppt_generator = PptGenerator(gemini_client)
content_expander = ContentExpander()

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptPreviewRequest(BaseModel):
    course_id: int
    generation_spec: dict
    blueprint: dict | None = None
    kg_outline: dict | None = None
    
@app.post("/prompt/preview")
async def preview_prompt(request: PromptPreviewRequest):
    try:
        builder = PromptBuilder(
            spec=request.generation_spec,
            blueprint=request.blueprint or {},
            outline=request.kg_outline
        )
        return builder.build_bundle()
    except Exception as e:
        logger.error(f"Prompt preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class TopicSlideGenRequest(BaseModel):
    course_id: int
    module_id: str
    topic_id: str
    module_title: str
    topic_title: str
    blueprint: dict | None = None # Made optional for backward compatibility
    kg_outline: dict | None = None # New Source
    generation_spec: dict
    prompt_text: str | None = None
    key_concepts: list[str] = []
    prerequisites: list[str] = []

@app.post("/topics/slides/generate")
async def generate_topic_slides(req: TopicSlideGenRequest):
    """
    Generate 8-slide JSON deck for a specific topic using Gemini.
    """
    if not settings.GEMINI_API_KEY:
        # Fallback for dev/demo if no key: DO NOT CRASH, return mock
        # But per requirements we should try to use real one if available.
        logger.warning("No GEMINI_API_KEY. Returning mock data.")
        return {
            "title": req.topic_title,
            "slides": [
                {
                    "title": f"Mock Slide {i+1} for {req.topic_title}",
                    "bullets": ["Mock bullet 1", "Mock bullet 2"],
                    "speaker_notes": "Mock notes...",
                    "illustration_prompt": "A placeholder image",
                    "order": i+1
                }
                for i in range(8)
            ]
        }

    try:
        # 1. Build Scoped Prompt
        # Determine effective blueprint or use kg_outline
        # PromptBuilder expects a blueprint dict, we can pass empty if using outline,
        # OR we can pass the outline AS blueprint if schema matches?
        # NO, schema is different. We should pass kg_outline as 'outline' arg.
        
        effective_blueprint = req.blueprint or {}
        
        builder = PromptBuilder(
            spec=req.generation_spec,
            blueprint=effective_blueprint,
            outline=req.kg_outline,
            topic_context={
                "module_id": req.module_id,
                "topic_id": req.topic_id,
                "module_title": req.module_title,
                "topic_title": req.topic_title
            },
            key_concepts=req.key_concepts,
            prerequisites=req.prerequisites,
            global_instructions=req.prompt_text
        )
        bundle = builder.build_bundle()
        prompt_text = bundle["rendered_prompt"]

        # 2. Call Generator
        # PptGenerator.generate_slide_plan returns {"slides": [...]} structure
        slide_plan = await ppt_generator.generate_slide_plan(prompt_text, effective_blueprint)
        
        # 3. Validation / Enforce 8 slides (Best effort)
        start_slides = slide_plan.get("slides", [])
        
        # If LLM returned fewer/more, maybe we just accept or trim/pad?
        # Requirement: "Exactly 8 slides per topic enforced"
        # If < 8, we can duplicate or just pass. 
        # If > 8, trim.
        
        final_slides = start_slides[:8]
        if len(final_slides) < 8:
            # Pad with summary/Q&A if needed
            while len(final_slides) < 8:
                idx = len(final_slides) + 1
                final_slides.append({
                    "title": "Extra Context / Reserve Slide",
                    "bullets": ["Additional notes", "Review key concepts"],
                    "speaker_notes": "Reserve slide for pacing.",
                    "illustration_prompt": "Abstract educational background",
                    "order": idx
                })
        
        # Normalize keys (illustration vs illustration_prompt)
        for i, s in enumerate(final_slides):
            s["order"] = i + 1
            # Normalize keys
            if "slide_title" in s and "title" not in s:
                s["title"] = s["slide_title"]
            if "slide_title" in s: s.pop("slide_title")
                
            if "illustration" in s and "illustration_prompt" not in s:
                s["illustration_prompt"] = s["illustration"]
            if "illustration" in s: s.pop("illustration")
            
            if "notes" in s and "speaker_notes" not in s:
                s["speaker_notes"] = s["notes"]
            if "notes" in s: s.pop("notes")
        
        return {
            "title": req.topic_title,
            "slides": final_slides
        }

    except Exception as e:
        logger.error(f"Topic generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    await kafka_client.start_producer()
    # Start consumer in background
    asyncio.create_task(kafka_client.start_consumer(
        topics=["course.events"],
        callback=process_event,
        group_id="ai-authoring-group"
    ))

@app.on_event("shutdown")
async def shutdown_event():
    await kafka_client.stop()

async def process_event(topic: str, message: dict):
    """Callback for consuming events"""
    # Phase 2: Generation only on explicit request
    # Phase 2: Generation only on explicit request
    if "prompt_text" in message:
        # Check if it is PPT request (has blueprint)
        if "blueprint" in message:
             logger.info(f"Received PPT_REQUEST for course {message.get('course_id')}")
             asyncio.create_task(handle_ppt_request(message))
        else:
             logger.info(f"Received GENERATION_REQUEST (Legacy) for course {message.get('course_id')}")
             asyncio.create_task(generate_content_from_request(message))
             
    elif "output_formats" in message and "slide_plan" in message:
        logger.info(f"Received FULL_CONTENT_REQUEST for course {message.get('course_id')}")
        asyncio.create_task(handle_content_request(message))
        
    elif "title" in message and "content" not in message:
        # Phase 1: Just log, do NOT auto-generate
        logger.info(f"Course created {message.get('course_id')}. Waiting for Phase-2 generation request.")

async def handle_ppt_request(event_data: dict):
    course_id = event_data['course_id']
    try:
        slide_plan = await ppt_generator.generate_slide_plan(
            event_data['prompt_text'],
            event_data['blueprint']
        )
        
        # Render PPTX
        # In Docker, we might need Xvfb for some ppt libs but python-pptx is pure python.
        ppt_path = await ppt_generator.render_pptx(slide_plan, course_id)
        
        # Determine URL or relative path for frontend
        # Assuming volume mount /app/data1 is accessible by frontend/exporter too?
        # Or just store path metadata.
        
        payload = PPTGeneratedPayload(
            course_id=course_id,
            slide_plan=slide_plan,
            ppt_artifact={"path": ppt_path, "filename": os.path.basename(ppt_path)}
        )
        
        await kafka_client.publish("course.events", payload.dict())
        logger.info(f"✅ Published PPT_READY for course {course_id}")
        
    except Exception as e:
        logger.error(f"PPT Generation failed: {e}")

async def handle_content_request(event_data: dict):
    course_id = event_data['course_id']
    try:
        artifacts = content_expander.expand_content(
            event_data['slide_plan'],
            course_id
        )
        
        # Construct content dict for indexing/storage
        # For now just store the paths or simple text? 
        # ContentGeneratedPayload expects 'content' dict.
        # We can put structure here.
        
        content_wrapper = {
            "summary": "Generated content",
            "artifacts": artifacts,
            # We should probably parse the TXT back or just store metadata
        }
        
        payload = ContentGeneratedPayload(
            course_id=course_id,
            content=content_wrapper
        )
        
        await kafka_client.publish("course.events", payload.dict())
        logger.info(f"✅ Published CONTENT_READY for course {course_id}")
        
    except Exception as e:
        logger.error(f"Content Expansion failed: {e}")

async def generate_content_from_request(event_data: dict):
    """Generate content using provided prompt and spec"""
    course_id = event_data['course_id']
    prompt_text = event_data.get('prompt_text')
    
    # We still fetch course basic info for metadata if needed, 
    # but primarily we use the prompt_text.
    # However, to keep the return payload consistent (ContentGeneratedPayload),
    # we might just return what Gemini gives us.
    
    logger.info(f"Generating content for course {course_id} using custom prompt...")
    
    try:
        # Construct a dummy course context wrapper if needed by existing signature, 
        # or just pass metadata.
        # existing generate_course_content expects 'title' etc for internally building prompt
        # BUT if we pass prompt_override, it skips that.
        # So we just need a dummy dict.
        dummy_data = {"title": f"Course {course_id}"} 
        
        generated_content = await gemini_client.generate_course_content(dummy_data, prompt_override=prompt_text)
        
        payload = ContentGeneratedPayload(
            course_id=course_id,
            content=generated_content
        )
        
        await kafka_client.publish("course.events", payload.dict())
        logger.info(f"✅ Published generated content for course {course_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate content for course {course_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

class DraftPromptRequest(BaseModel):
    course_id: int
    course_title: str
    course_description: str
    blueprint_summary: str | None = None

@app.post("/draft-prompt")
async def draft_prompt(req: DraftPromptRequest):
    """Helper to build a prompt with RAG context for the Frontend to display"""
    query = f"{req.course_title} {req.course_description}"
    query = f"{req.course_title} {req.course_description}"
    
    if not settings.GEMINI_API_KEY:
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot draft prompt.")
         
    context = gemini_client.retrieve_context(query, course_id=req.course_id)
    
    # Simple template
    prompt = f"""You are an expert curriculum designer.
Course: {req.course_title}
Context: {context[:2000]}...

Blueprint Summary:
{req.blueprint_summary or 'N/A'}

Task: Generate detailed course content following OBE standards.
... [User can edit this] ...
"""
    return {"prompt_text": prompt, "context_snippet": context[:200]}

class PromptBuildRequest(BaseModel):
    course_id: int
    blueprint: dict
    generation_spec: dict
    bloom: dict | None = None  # Added to capture Step 5 payload
    references: dict | None = None # Phase 2: Strict Reference Map

def normalize_id(id_val):
    """Helper for ID normalization (UNIT 1 -> U1)"""
    s = str(id_val).strip().upper()
    import re
    m = re.match(r"^UNIT\s*(\d+)$", s)
    if m:
        return f"U{m.group(1)}"
    return s

def normalize_generation_spec(spec: dict) -> dict:
    """
    Normalize generation spec to support both legacy and new frontend formats.
    
    Frontend (Step 4) -> Backend Canonical:
    - pedagogy_checklist -> pedagogy
    - output_constraints.max_slides -> constraints.ppt.max_slides
    - output_constraints.font_size_min -> constraints.ppt.font_size_min
    - output_constraints.word_limit -> constraints.ppt.word_limit
    - output_constraints.bloom_policy.global_default -> bloom.default_level
    """
    norm = spec.copy()
    
    # 1. Pedagogy
    if "pedagogy" not in norm and "pedagogy_checklist" in norm:
        norm["pedagogy"] = norm["pedagogy_checklist"]
        
    # 2. Constraints (Frontend sends output_constraints)
    if "constraints" not in norm:
        norm["constraints"] = {}
        
    if "ppt" not in norm["constraints"]:
        norm["constraints"]["ppt"] = {}
        
    out_constraints = norm.get("output_constraints", {})
    
    # Map fields if missing in target
    ppt_constraints = norm["constraints"]["ppt"]
    if "max_slides" not in ppt_constraints and "max_slides" in out_constraints:
        ppt_constraints["max_slides"] = out_constraints["max_slides"]
        
    if "font_size_min" not in ppt_constraints and "font_size_min" in out_constraints:
        ppt_constraints["font_size_min"] = out_constraints["font_size_min"]
        
    if "word_limit" not in ppt_constraints and "word_limit" in out_constraints:
        ppt_constraints["word_limit"] = out_constraints["word_limit"]
        
    if "bullets_per_slide_max" not in ppt_constraints:
         # Some frontends might send this or we default
         pass 

    return norm

@app.post("/prompts/build")
async def build_prompt(req: PromptBuildRequest):
    """
    Build the best prompt for course generation using Blueprint + Specs + RAG.
    Adheres to STRICT Master Prompt rules from Client Requirements.
    """
    try:
        if not settings.GEMINI_API_KEY:
             raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot build prompt.")

        # --- 0. Normalization ---
        req.generation_spec = normalize_generation_spec(req.generation_spec)
        
        # --- 1. Validation & Extraction ---
        
        # Identity
        course_title = req.blueprint.get("course_identity", {}).get("course_name", "Untitled Course")
        description = req.blueprint.get("course_identity", {}).get("description", "")
        
        # Scope Calculation
        # Scope Calculation
        # Support new hierarchy_scope (Phase 5) and legacy hierarchy
        hierarchy_scope = req.generation_spec.get("hierarchy_scope") or req.generation_spec.get("hierarchy", {})
        
        # Modules can be list of IDs (legacy) or list of objects (new)
        raw_modules = hierarchy_scope.get("modules") or hierarchy_scope.get("scope_modules", [])
        
        scope_module_ids = []
        for item in raw_modules:
            if isinstance(item, dict):
                # {module_id: "...", module_name: "..."}
                mid = item.get("module_id") or item.get("id")
                if mid:
                    scope_module_ids.append(str(mid))
            else:
                scope_module_ids.append(str(item))

        # Fallback to selection object if hierarchy scope is minimal
        if not scope_module_ids and "selection" in req.generation_spec:
             scope_module_ids = req.generation_spec["selection"].get("module_ids", [])
             
        # Helper for ID normalization - Moved to module level
        
        # Canonicalize scope IDs
        scope_module_ids = [normalize_id(str(x)) for x in scope_module_ids]
    
        logger.info(f"DEBUG: scope_module_ids={scope_module_ids}")
        blueprint_raw_ids = [m.get('id') for m in req.blueprint.get('modules', [])]
        logger.info(f"DEBUG: blueprint_ids(raw)={blueprint_raw_ids}")
        
        if not scope_module_ids:
             logger.error("No modules selected in scope.")
             raise HTTPException(status_code=400, detail="No modules selected. Please select at least one module.")

        # Extract Module Details for Context Injection (Title + Topics)
        blueprint_modules = req.blueprint.get("modules", [])
        selected_modules_details = []
        
        for m in blueprint_modules:
            m_id = str(m.get("id"))
            # Check both raw and normalized to be safe
            if m_id in scope_module_ids or normalize_id(m_id) in scope_module_ids:
                selected_modules_details.append(m)
                
        if not selected_modules_details:
             logger.error(f"Selected modules not found. Scope:{scope_module_ids} vs Blueprint:{blueprint_raw_ids}")
             raise HTTPException(status_code=400, detail="Selected modules not found in blueprint.")

        # Inputs
        checklist = req.generation_spec.get("pedagogy", [])
        constraints = req.generation_spec.get("constraints", {})
        bloom_data = req.bloom or {}
        
        # Bloom Normalization (Frontend sends in output_constraints.bloom_policy sometimes)
        if not bloom_data:
             policy = req.generation_spec.get("output_constraints", {}).get("bloom_policy", {})
             if policy:
                 bloom_data = {"default_level": policy.get("global_default", "Apply"), "overrides": {}}
             elif "bloom" in req.generation_spec:
                 # Support legacy nesting key
                 bloom_data = req.generation_spec["bloom"]

        time_plan = req.generation_spec.get("time_plan", {})
        
        # --- 2. Prompt Block Construction ---
        
        # A) Selected Modules Block
        modules_block = "[SELECTED MODULES]\n"
        for m in selected_modules_details:
            modules_block += f"- Module {m.get('id')}: {m.get('title')}\n"
            topics = m.get("topics", [])
            for t in topics:
                 modules_block += f"  * Topic {t.get('id')}: {t.get('name')} (Outcome: {t.get('topic_outcome', 'Not Provided')})\n"

        # B) Content Hierarchy Rules
        hierarchy_rules = """[CONTENT HIERARCHY RULES]
- Slides MUST be grouped module-wise.
- Each module starts with 1 overview slide: title + module outcome + topic list.
- Topics MUST appear only under their parent module (no cross-module mixing).
- Subtopics optional; if missing, do not invent.
- If topic outcome is missing, output "Not Provided" (do NOT infer)."""

        # C) Bloom Control (Per Topic)
        default_bloom = bloom_data.get("default_level", "Apply")
        bloom_overrides = bloom_data.get("overrides", {})
        
        bloom_section = "[BLOOM CONTROL — PER TOPIC]\n"
        bloom_section += f"Default Level: {default_bloom}\n"
        bloom_section += "Overrides (MUST FOLLOW):\n"
        
        has_overrides = False
        for m in selected_modules_details:
            for t in m.get("topics", []):
                tid = str(t.get("id"))
                level = bloom_overrides.get(tid, default_bloom)
                bloom_section += f"- Mod {m.get('id')} / Topic {tid}: {level}\n"
                has_overrides = True
        
        if not has_overrides:
             bloom_section += f"(Applies '{default_bloom}' to all topics if no specific overrides)\n"

        # D) Time & Density Rules
        # D) Time & Density Rules
        # Prefer direct minutes (Phase 5), fallback to hours * 60 (Legacy)
        spec_duration = req.generation_spec.get("total_duration_minutes")
        if spec_duration is None:
             spec_duration = req.generation_spec.get("total_duration", 0) * 60
             
        total_duration = time_plan.get("total_minutes", spec_duration)
        topic_times = time_plan.get("topic_minutes", {})
        
        # Phase 6: Time Distribution Fallback
        time_dist = req.generation_spec.get("time_distribution", {})
        if not topic_times and time_dist:
             # If manual 'topic_minutes' missing, use distribution strategy
             default_mins = time_dist.get("topic_minutes_default", 0)
             # We can't easily map module_minutes to topics unless we distribute evenly again
             # For prompt display, if we don't have per-topic overrides, we state the default
             if default_mins > 0:
                 for m in selected_modules_details:
                     for t in m.get("topics", []):
                         topic_times[str(t.get("id"))] = default_mins
        
        time_section = f"""[TIME & DENSITY RULES]
- Total Course Duration: {total_duration} minutes
- Default Density: ~1 slide per minute
- Max Slides: {constraints.get('ppt', {}).get('max_slides', 20)}
- Bullets per Slide: Max {constraints.get('ppt', {}).get('bullets_per_slide_max', 5)}
- Speaker Notes: Must align with topic duration.
- Per-Topic Allocations:
- Slide Count Rule: EXACTLY 8 slides per topic.
- Subtopic Rule: At least 1 slide per subtopic.
"""
        for tid, mins in topic_times.items():
             time_section += f"  * Topic {tid}: {mins} mins\n"

        # E) Pedagogy Checklist
        pedagogy_section = f"""[PEDAGOGY CHECKLIST]
- Include: {', '.join(checklist)}
- Ordering: Follow logical progression (Intro -> Concept -> Example -> Summary)
- Do not invent pedagogy items not listed."""

        # F) Reference Grounding via RAG
        # 1. Strict Whitelist Construction
        allowed_files = []
        topic_ref_map = {}
        if req.references and "references" in req.references:
            for ref in req.references["references"]:
                 if ref.get("file_path"):
                     allowed_files.append(ref["file_path"])
                 if ref.get("level") == "topic" and ref.get("topic_id"):
                     topic_ref_map.setdefault(ref["topic_id"], []).append(ref["file_path"])
        
        # 2. Context Retrieval (Course Level)
        query = f"{course_title} {description}"
        context_parts = []
        
        # Pass allowed_files to RAG
        course_ctx = gemini_client.retrieve_context(
            query, 
            course_id=req.course_id, 
            limit=3,
            allowed_filenames=allowed_files if allowed_files else None
        )
        if course_ctx:
             context_parts.append(f"--- From Course References ---\n{course_ctx}")
             
        # 3. Module Level (Iterate over scope)
        for m in selected_modules_details:
             mod_id = m.get("id")
             mod_query = f"Module {m.get('title')} {query}"
             
             # Check for Module/Topic specific overrides?
             # For now, we trust vector store filtering by module_id if we passed it?
             # But we also want to filter by filename.
             
             mod_ctx = gemini_client.retrieve_context(
                 mod_query, 
                 course_id=req.course_id, 
                 module_id=mod_id, 
                 limit=3,
                 allowed_filenames=allowed_files if allowed_files else None
             )
             if mod_ctx:
                 context_parts.append(f"--- From Module {mod_id} References ---\n{mod_ctx}")
                 
        # 4. Low Evidence Marking in Modules Block (Retroactive Update)
        # We need to rebuild modules_block to include "Low Evidence" warning for unmapped topics
        # Recalculate modules_block
        modules_block = "[SELECTED MODULES]\n"
        for m in selected_modules_details:
            modules_block += f"- Module {m.get('id')}: {m.get('title')}\n"
            topics = m.get("topics", [])
            for t in topics:
                 tid = str(t.get("id"))
                 tname = t.get("name")
                 outcome = t.get("topic_outcome", "Not Provided")
                 
                 # Check if mapped
                 # Logic: If map exists but topic NOT in map -> Low Evidence
                 # If map is empty -> All Low Evidence? Or All High (default)?
                 # Requirement: "If a topic has no mapped reference... Mark topic as 'Low Evidence'"
                 is_mapped = tid in topic_ref_map
                 
                 # Conservative: If we have ANY references, we enforce mapping. If NO references whatsoever, maybe Blueprint only?
                 # Prompt engine rule: "Topics without mapped references are explicitly marked"
                 
                 suffix = ""
                 if req.references and req.references.get("references") and not is_mapped:
                      suffix = " (Low Evidence - Follow Blueprint Strictly)"
                 
                 modules_block += f"  * Topic {tid}: {tname} (Outcome: {outcome}){suffix}\n"
        
        full_context = "\n\n".join(context_parts)
        if not full_context:
            full_context = "No specific references found. STRICTLY USE BLUEPRINT DATA."

        grounding_section = f"""[REFERENCE MATERIAL GROUNDING]
Context from Reference Materials:
{full_context[:6000]}

- Use ONLY content present in Syllabus (Blueprint) or Reference Materials above.
- If a concept is not present, mark it "Not Provided in References" instead of inventing."""

        # G) Anti-Hallucination Guardrails
        guardrails_section = """[ANTI-HALLUCINATION RULES]
- Do NOT introduce topics, standards, formulas, processes, or examples not present in blueprint/references.
- Do NOT add extra modules not selected.
- If info missing: write "Not Provided in Blueprint" in speaker notes and output JSON.
- Output MUST remain within constraints."""

        # --- 3. Final Prompt Assembly ---
        prompt = f"""You are an Expert Curriculum Designer.
Course: {course_title}

{modules_block}

{hierarchy_rules}

{bloom_section}

{time_section}

{pedagogy_section}

{grounding_section}

{guardrails_section}

Task:
Generate a detailed Slide Plan for a PPT presentation covering the selected modules.
ALL instructions above are MANDATORY.

Output Format: JSON (Strict)
Schema:
{{
  "course_title": "string",
  "selected_modules": [ {{ "id": "string", "title": "string" }} ],
  "slides": [
    {{
      "slide_no": int,
      "module_id": "string",
      "module_title": "string",
      "topic_id": "string",
      "topic_title": "string",
      "bloom_level": "string",
      "time_minutes": int,
      "title": "string",
      "bullets": ["string"],
      "illustration_prompt": "string (Prompt for generating image)",
      "speaker_notes": "string (detailed)"
    }}
  ],
  "warnings": ["string"]
}}
"""
        logger.info(f"Generated Prompt for Course {req.course_id} (Length: {len(prompt)})")
        # logger.debug("Prompt Content:\n" + prompt) 

        return {"prompt_text": prompt, "context_snippet": full_context[:500]}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Prompt build failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-content")
async def generate_content(request: dict):
    """
    Generate content using MCP Router.
    Request body:
    {
        "course_id": int,
        "module_id": int,
        "topic_id": int,
        "subtopic_id": int,
        "prompt": str,
        "mode": "design" | "tutoring"
    }
    """
    from shared.mcp_router import MCPRouter, ModelType
    
    if not settings.GEMINI_API_KEY:
         # Use dict return for this endpoint structure? Or HTTP 400?
         # Existing error returns {"status": "error"}.
         # But User requested 400.
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured.")
         
    # Initialize Router
    router = MCPRouter(api_key=settings.GEMINI_API_KEY)
    
    prompt = request.get("prompt")
    mode = request.get("mode", "design")
    course_id = request.get("course_id")
    module_id = request.get("module_id")
    
    logger.info(f"👉 GENERATE REQUEST: payload={request}")
    logger.info(f"👉 Context: course_id={course_id} (type {type(course_id)}), module_id={module_id}")
    
    # Map mode to ModelType
    task_type = ModelType.DESIGN if mode == "design" else ModelType.TUTORING
    
    # 1. Relevance Check (Hard Fail)
    # Use scoped relevance check
    is_relevant = await gemini_client.check_relevance(prompt, course_id=course_id, module_id=module_id)
    if not is_relevant:
        return {
            "status": "rejected",
            "message": "Your prompt is not relevant to the selected module/topic content. Please provide a more focused instructional prompt."
        }
    
    # 2. Retrieve Context (if relevant)
    # Reuse GeminiClient context retrieval or do it here
    # For Phase-1, let's keep it simple and just pass the prompt to MCP
    
    # 3. Route to LLM via MCP
    try:
        result = await router.route_request(task_type, prompt)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
