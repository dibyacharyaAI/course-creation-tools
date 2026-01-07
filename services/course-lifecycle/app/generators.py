import math
import re
from .evidence_retriever import retrieve_evidence_sync # New Sync Wrapper

def get_canonical_id(id_str):
    """Normalize 'UNIT 1' or 'U1' to 'U1' for logic lookups"""
    if not id_str: return ""
    s = str(id_str).strip().upper()
    m = re.match(r"^UNIT\s*(\d+)$", s)
    if m:
        return f"U{m.group(1)}"
    return s

def generate_deterministic_outline(blueprint: dict, generation_spec: dict = None, deck_mode: str = "QUICK_DECK", max_slides_override: int = None) -> dict:
    """
    Generates a deterministic PPT outline JSON based on the blueprint and specs.
    No LLM involved. STRICT ADHERENCE to blueprint structure.
    CONTRACT V4: FULL_COVERAGE support + metadata fields.
    """

    # --- 1. CONFIGURATION ---
    # Handle DB schema vs File schema vars
    course_title = blueprint.get('course', {}).get('course_title', "Course")
    if not course_title:
        course_title = blueprint.get('course_identity', {}).get('course_title', "Course")
    
    course_id = 0
    if generation_spec:
        course_id = generation_spec.get('course_id', 0)
    
    # We need course_id for RAG retrieval. Ideally passed in arguments, but blueprint might have it or we infer?
    # Actually `generation_spec` has `course_id`.
    course_id = 0
    if generation_spec:
        course_id = generation_spec.get('course_id', 0)

    modules = blueprint.get('modules', [])
    MAX_TOPICS_PER_SLIDE = 2 # Assuming 2 topics per slide constant

    # Deck Limit
    MAX_SLIDES_GLOBAL = 15 # Default limit for Quick Deck
    if max_slides_override:
        MAX_SLIDES_GLOBAL = int(max_slides_override)
    elif generation_spec and generation_spec.get('output_constraints'):
        MAX_SLIDES_GLOBAL = generation_spec['output_constraints'].get('max_slides', 15)
        
    # Bloom Default
    bloom_default = "Apply"
    if generation_spec and generation_spec.get('output_constraints'):
        bloom_default = generation_spec['output_constraints'].get('bloom_policy', {}).get('global_default', "Apply")

    # --- 2. DETERMINE REQUIREMENTS (Phase 2D) ---
    total_topics = 0
    valid_modules = []
    
    # Pre-scan for valid topics
    for m in modules:
        valid_topics = [t for t in m.get('topics', []) if (t.get('topic_name') or t.get('name'))]
        if valid_topics:
            total_topics += len(valid_topics)
            valid_modules.append({"m": m, "topics": valid_topics})

    intro_slide_count = 1
    # Required slides = Intro + Ceil(Topics / 2)
    required_slides = intro_slide_count + math.ceil(total_topics / MAX_TOPICS_PER_SLIDE)

    # --- 3. MODE ENFORCEMENT ---
    # Mode Handling: Aliasing or Legacy Support
    if deck_mode == "CLIENT_STRICT": deck_mode = "FULL_COVERAGE"
    if deck_mode not in ["QUICK_DECK", "FULL_COVERAGE"]: deck_mode = "QUICK_DECK"

    slides_per_module = None # If None, uncapped (FULL COVERAGE behavior)
    coverage_warnings = []

    # LOGIC 1: If we can fit everything, just do it (No skipping)
    if required_slides <= MAX_SLIDES_GLOBAL:
        # Fits comfortably. Force FULL_COVERAGE behavior effectively
        slides_per_module = None
    else:
        # LOGIC 2: Overflow Handling
        if deck_mode == "FULL_COVERAGE":
            # Must NOT skip -> Return Blocker Error
            return {
                "error": "MAX_SLIDES_TOO_LOW",
                "required_min_slides": required_slides,
                "given_max_slides": MAX_SLIDES_GLOBAL,
                "message": f"Full Coverage requires {required_slides} slides, but limit is {MAX_SLIDES_GLOBAL}. Switch to Quick Deck or increase limit."
            }
        else:
            # QUICK_DECK -> Apply Caps (Skip allowed)
            available_slides = MAX_SLIDES_GLOBAL - intro_slide_count
            if available_slides < len(valid_modules):
                available_slides = len(valid_modules) # Min 1 per module soft fail
            
            # Simple Distribution: Even split
            slides_per_module = {}
            base_alloc = available_slides // len(valid_modules)
            remainder = available_slides % len(valid_modules)
            
            for idx, vm in enumerate(valid_modules):
                m = vm['m']
                mid = get_canonical_id(m.get('module_id') or m.get('id'))
                alloc = base_alloc
                if idx < remainder: 
                    alloc += 1
                slides_per_module[mid] = alloc

    # --- 4. GENERATION LOOP ---
    slides = []
    slide_counter = 1
    
    # Intro Slide
    intro_slide = {
        "slide_id": f"S{slide_counter}",
        "slide_no": slide_counter,
        "slide_title": f"{course_title}: Overview",
        "module_id": "U0",
        "module_label": "INTRO",
        "module_name": "Course Introduction",
        "topics_covered": [],
        "bloom_level": "Understand",
        "minutes_allocated": 10,
        "evidence_used": ["syllabus_blueprint:course"],
        "claims": [],
        "evidence_map_ref": {},
        "flags": ["Low Evidence - Follow Blueprint Strictly"]
    }
    slides.append(intro_slide)
    slide_counter += 1

    unit_map = { "U1": "UNIT 1", "U2": "UNIT 2", "U3": "UNIT 3", "U4": "UNIT 4", "U5": "UNIT 5", "U6": "UNIT 6" }

    for m_idx, vm in enumerate(valid_modules):
        m = vm['m']
        topics = vm['topics']
        
        raw_mid = m.get('module_id') or m.get('id')
        m_name = m.get('module_name') or m.get('name') or m.get('title')
        canonical_mid = get_canonical_id(raw_mid)
        # Fallback if raw_mid is not U# format
        if not canonical_mid.startswith("U"):
            canonical_mid = f"U{m_idx + 1}"
            
        display_label = unit_map.get(canonical_mid, raw_mid)

        # Determine target slide count
        target_count = 999
        if slides_per_module:
            target_count = slides_per_module.get(canonical_mid, 1)

        # Calculate max coverable
        max_coverable_topics = target_count * MAX_TOPICS_PER_SLIDE
        
        topics_to_cover = topics
        if len(topics) > max_coverable_topics:
            topics_to_cover = topics[:max_coverable_topics]
            skipped = topics[max_coverable_topics:]
            if skipped:
                count = len(skipped)
                s_names = ", ".join([t.get('topic_name') or t.get('name') for t in skipped[:2]])
                coverage_warnings.append(f"Skipped {count} topics in {display_label} (e.g. {s_names}...)")

        # Chunking
        topic_chunks = [topics_to_cover[i:i + MAX_TOPICS_PER_SLIDE] for i in range(0, len(topics_to_cover), MAX_TOPICS_PER_SLIDE)]

        for t_chunk_idx, chunk in enumerate(topic_chunks):
            def get_t_name(t): return t.get('topic_name') or t.get('name') or "Untitled"

            title_topics = ", ".join([
                get_t_name(t)[:40] + "..." if len(get_t_name(t)) > 40 else get_t_name(t)
                for t in chunk
            ])
            
            topics_data = []
            evidence_keys = []
            
            slide_claims = []
            slide_evidence_map = {}
            
            for t_idx, t in enumerate(chunk):
                # Canonical Topic ID: U#T#
                tid = t.get('topic_id') or t.get('id')
                
                # Logic: Use unit ID + index within unit
                original_idx = topics.index(t) + 1
                canonical_tid = f"{canonical_mid}T{original_idx}"
                
                tname = get_t_name(t)
                topics_data.append({"topic_id": canonical_tid, "topic_name": tname})
                evidence_keys.append(f"syllabus_blueprint:{canonical_tid}")
                
                # REAL RAG RETRIEVAL (Synchronous)
                if course_id > 0:
                    query = f"{m_name}: {tname}"
                    retrieved_items = retrieve_evidence_sync(course_id, query)
                    
                    if retrieved_items:
                        claim_id = f"c_{canonical_tid}_1"
                        slide_claims.append({
                            "claim_id": claim_id, 
                            "text": f"Overview of {tname}",
                            "citations": [r['source_id'] for r in retrieved_items[:2]]
                        })
                        
                        for r in retrieved_items[:2]:
                            src_id = r.get("source_id", "unknown")
                            # Simple simplified contract logic
                            slide_evidence_map[src_id] = {
                                "source_id": src_id,
                                "source_type": "knowledge_base",
                                "locator": str(r.get("metadata", {}).get("page_label", "N/A")),
                                "snippet": r.get("text", "")[:200]
                            }
                    
                    if retrieved_items:
                        # Convert to Claim/Evidence format
                        # For now, we will just create a "General Topic Claim" and attach evidence
                        claim_id = f"c_{canonical_tid}_1"
                        slide_claims.append({
                            "claim_id": claim_id, 
                            "text": f"Overview of {tname}",
                            "citations": [r['source_id'] for r in retrieved_items[:2]]
                        })
                        
                        for r in retrieved_items[:2]:
                            # Map to EvidenceItem
                            # r is dict from rag-indexer: {source, type, ...}
                            # Assuming rag returns fields we need
                            src_id = r.get("source_id", "unknown")
                            # Populate map
                            slide_evidence_map[src_id] = {
                                "source_id": src_id,
                                "source_type": "knowledge_base",
                                "locator": str(r.get("metadata", {}).get("page_label", "N/A")),
                                "snippet": r.get("text", "")[:200]
                            }

            slides.append({
                "slide_id": f"S{slide_counter}",
                "slide_no": slide_counter,
                "slide_title": f"{display_label}: {title_topics}",
                "module_id": canonical_mid, 
                "module_label": display_label, 
                "module_name": m_name,
                "topics_covered": topics_data,
                "bloom_level": bloom_default,
                "minutes_allocated": 15, 
                "evidence_used": evidence_keys,
                "claims": slide_claims,
                "evidence_map_ref": slide_evidence_map if slide_evidence_map else None,
                "flags": ["Real RAG Enabled" if slide_claims else "Low Evidence"]
            })
            slide_counter += 1

    # --- 5. FINALIZE ---
    total_slides = len(slides)
    deck_duration_minutes = sum([s.get("minutes_allocated", 0) for s in slides])
    
    # Try to find course total duration from blueprint or spec
    course_duration_minutes = 3600 # Default fallback
    if generation_spec and generation_spec.get('target_duration_minutes'):
         course_duration_minutes = generation_spec.get('target_duration_minutes')
    elif generation_spec and generation_spec.get('total_duration_minutes'):
         course_duration_minutes = generation_spec.get('total_duration_minutes')
    elif blueprint.get('course', {}).get('duration_minutes'):
         course_duration_minutes = blueprint.get('course', {}).get('duration_minutes')

    return {
        "total_slides": total_slides,
        "computed_total_slides": total_slides,
        "estimated_duration_minutes": deck_duration_minutes, # Keep for backward compatibility
        "deck_duration_minutes": deck_duration_minutes,
        "course_duration_minutes": course_duration_minutes,
        "duration_semantics": "course_duration_minutes != deck_duration_minutes in QUICK_DECK",
        "required_min_slides": required_slides,
        "current_max_slides": MAX_SLIDES_GLOBAL,
        "slides": slides,
        "coverage_warnings": coverage_warnings,
        "deck_mode": deck_mode
    }
