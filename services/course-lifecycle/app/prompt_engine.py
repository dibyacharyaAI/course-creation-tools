import json

def build_ppt_prompt(blueprint: dict, outline: dict, deck_mode: str, generation_spec: dict = None, evidence_map: dict = None, grounding_strictness: str = "NORMAL") -> str:
    """
    Constructs the Mega Prompt for the LLM to generate slide content.
    Follows strict constraints, outline structure, and evidence grounding.
    Phase 3A: Full Implementation.
    """
    
    course_title = blueprint.get('course', {}).get('course_title') or blueprint.get('course_identity', {}).get('course_title', "Course")
    evidence_map = evidence_map or {}
    generation_spec = generation_spec or {}
    constraints = generation_spec.get('output_constraints', {})
    
    # 1. Role & Task
    prompt = [
        "Role: Educational Content Architect.",
        f"Task: Create detailed slide content for the course '{course_title}'.",
        "You must follow the provided OUTLINE EXACTLY. Do not add, remove, or reorder slides.",
        "Your output must be a single valid JSON object containing a 'slides' array.",
        ""
    ]

    # 2. Strict Constraints (Global)
    prompt.append("--- GLOBAL CONSTRAINTS ---")
    prompt.append(f"1. Max lines per slide: {constraints.get('max_lines_per_slide', 12)}")
    prompt.append(f"2. Max words per line: {constraints.get('max_words_per_line', 15)}")
    prompt.append(f"3. Min font size (for context): {constraints.get('font_size_min', 18)}")
    prompt.append("4. Use bullet points only for content. NO paragraphs in 'bullets' array.")
    prompt.append("5. Speaker notes should be comprehensive, narrative, and engaging.")
    prompt.append("")

    # 3. Grounding & Strictness Rules
    prompt.append("--- GROUNDING RULES ---")
    if grounding_strictness in ["STRICT", "NORMAL"]:
        prompt.append("STRICT GROUNDING ENFORCED:")
        prompt.append("1. All factual claims in bullet points MUST be supported by the provided 'EVIDENCE MATERIAL'.")
        prompt.append("2. If a topic has NO evidence provided below:")
        prompt.append("   - Do NOT invent content.")
        prompt.append("   - Instead, generate a 'Practice/Activity' slide asking students to research/discuss the topic.")
        prompt.append("   - Mark the slide as 'UNGROUNDED'.")
    else: # DRAFT
        prompt.append("DRAFT MODE GROUNDING:")
        prompt.append("1. Use provided evidence where available.")
        prompt.append("2. If evidence is missing, you MAY use your general knowledge, but you must mark the slide as 'UNGROUNDED'.")
    prompt.append("")

    # 4. Input Context: Outline & Slides
    prompt.append("--- OUTLINE & SLIDE INSTRUCTIONS (STRICT ADHERENCE REQUIRED) ---")
    
    slides_out = outline.get('slides', [])
    for slide in slides_out:
        sid = slide.get('slide_id')
        title = slide.get('slide_title')
        topics = slide.get('topics_covered', [])
        t_names = [t['topic_name'] for t in topics]
        
        prompt.append(f"SLIDE {sid}: {title}")
        prompt.append(f"  - Topics: {', '.join(t_names)}")
        if not t_names and slide.get('module_label') == "INTRO":
            prompt.append("  - Content: Course Overview, Objectives, Structure.")
            
        # Pedagogy Injection
        # Ideally we'd look up pedagogy per topic, but for now apply global checklist
        pedagogy = generation_spec.get('pedagogy_checklist', [])
        if pedagogy:
             prompt.append(f"  - Pedagogy Focus: {', '.join(pedagogy[:3])}") # First 3 for brevity
             
        prompt.append("")
        
    prompt.append("-------------------------------------------")

    # 5. Evidence Material Injection
    if evidence_map:
        prompt.append("--- EVIDENCE MATERIAL (Use ONLY this for grounding) ---")
        for tid, items in evidence_map.items():
            if items:
                prompt.append(f"TOPIC {tid}:")
                for i, item in enumerate(items):
                    prompt.append(f"  [Ref {i+1}] Source: {item.get('source_id')} | Locator: {item.get('locator')}")
                    prompt.append(f"  Snippet: {item.get('snippet', '')[:300]}...") 
                prompt.append("")
        prompt.append("-------------------------------------------------------")
    else:
        prompt.append("--- EVIDENCE MATERIAL ---")
        prompt.append("(No specific evidence available. Follow Grounding Rules for missing evidence.)")
        prompt.append("-------------------------")

    # 6. Quick Deck Specifics
    if deck_mode == "QUICK_DECK":
        prompt.append("CRITICAL QUICK_DECK INSTRUCTION:")
        prompt.append("This is a condensed deck. Do NOT invent or re-introduce skipped topics. Adhere strictly to the slide list above.")
        prompt.append("")

    # 7. Output Schema
    prompt.append("Output Schema (JSON ONLY):")
    prompt.append("""{
  "slides": [
    {
      "slide_id": "S1",
      "title": "Exact Title from Outline",
      "bullets": ["Bullet 1 (Claim c1)", "Bullet 2 (Claim c2)"],
      "speaker_notes": "Detailed notes...",
      "evidence_map": {
          "items": [
             {
               "claim_id": "c1",
               "claim_text": "Bullet 1 text",
               "evidence_refs": ["source_id_1"], 
               "grounding_status": "SUPPORTED" 
             }
          ],
          "overall_status": "GROUNDED"
      },
      "layout": "TITLE_AND_BULLETS"
    }
  ]
}""")
    prompt.append("Note: 'evidence_map' is required. 'grounding_status' can be 'SUPPORTED', 'PARTIAL', 'UNSUPPORTED', or 'UNGROUNDED'.")
    prompt.append("")

    return "\n".join(prompt)

def build_refine_prompt(blueprint: dict, current_slides: dict, verifier_errors: list, evidence_map: dict) -> str:
    """
    Constructs a repair prompt for the LLM to fix verification issues.
    """
    
    # 1. Role
    prompt = [
        "Role: Expert Editor and Fact-Checker.",
        "Task: Fix the following slide content which FAILED verification.",
        "GOAL: Ensure every factual claim has a valid citation from the provided evidence.",
        ""
    ]
    
    # 2. Issues
    prompt.append("--- VERIFICATION ISSUES ---")
    for err in verifier_errors:
        prompt.append(f"- Slide {err.get('slide_id')}: {', '.join(err.get('missing_points', []))}")
    prompt.append("")
    
    # 3. Current Content
    prompt.append("--- CURRENT SLIDES (Draft) ---")
    prompt.append(json.dumps(current_slides, indent=2))
    prompt.append("")
    
    # 4. Evidence (Reuse)
    prompt.append("--- AVAILABLE EVIDENCE (Use ONLY this) ---")
    if evidence_map:
        for tid, items in evidence_map.items():
             if items:
                prompt.append(f"TOPIC {tid}:")
                for i, item in enumerate(items):
                    prompt.append(f"  [Ref {i+1}] Source: {item.get('source_id')} | Locator: {item.get('locator')}")
                    prompt.append(f"  Snippet: {item.get('snippet', '')[:300]}...")
    else:
        prompt.append("(Nos evidence provided)")
    prompt.append("")
    
    # 5. Instructions
    prompt.append("--- REFINEMENT RULES ---")
    prompt.append("1. REVIEW each failing slide.")
    prompt.append("2. IF a bullet point has a factual claim but NO evidence:")
    prompt.append("   - REMOVE the bullet point, OR")
    prompt.append("   - REWRITE it as a question/discussion point (Practice/Activity) that implies uncertainty.")
    prompt.append("3. IF the entire slide is ungrounded and cannot be supported:")
    prompt.append("   - Convert it to a 'Practice/Activity' slide explicitly.")
    prompt.append("   - Set 'overall_status' in evidence_map to 'UNGROUNDED'.")
    prompt.append("4. DO NOT invent citations. Use only [Ref X] from above.")
    prompt.append("5. Maintain the original JSON structure EXACTLY.")
    prompt.append("")
    
    prompt.append("Output Schema (JSON ONLY):")
    prompt.append("""{ "slides": [ ... ] }""")
    
    return "\n".join(prompt)
