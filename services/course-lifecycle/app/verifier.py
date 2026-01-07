import datetime
from typing import List, Dict, Any
from .contracts import VerifierReport, SlideVerifierResult, VerifierStatus

def verify_slides(slides_data: Dict[str, Any], strictness: str = "NORMAL") -> VerifierReport:
    """
    Verifies the constraints and grounding of the generated slides.
    
    Args:
        slides_data: Dictionary containing list of slides (LLM output format)
        strictness: "STRICT", "NORMAL", or "DRAFT"
        
    Returns:
        VerifierReport
    """
    slides = slides_data.get("slides", [])
    if not slides:
        return VerifierReport(
            status=VerifierStatus.FAIL,
            coverage_pct=0.0,
            blockers=["No slides found in content."],
            timestamp=datetime.datetime.now().isoformat()
        )

    slide_results = []
    total_slides = len(slides)
    grounded_slides = 0
    blockers = []
    
    overall_status = VerifierStatus.PASS

    for slide in slides:
        slide_id = slide.get("slide_id", "Unknown")
        slide_title = slide.get("title", "Untitled")
        
        issues = []
        is_slide_grounded = True # Assume true until proven otherwise or explicit status found
        
        # 1. Grounding Usage Check
        # Check explicitly mapped claims (Phase 4A)
        claims = slide.get("claims", [])
        has_claims = len(claims) > 0

        # Check explicit evidence_map status if present
        ev_map = slide.get("evidence_map", {})
        ev_status = ev_map.get("overall_status", "UNKNOWN")
        
        # Check for bullets with citations (Legacy/Fallback)
        bullets = slide.get("bullets", [])
        has_citations = any("[" in b and "Ref" in b for b in bullets)
        
        if ev_status == "UNGROUNDED":
            is_slide_grounded = False
            issues.append("Marked as UNGROUNDED")
        elif not has_claims and not has_citations and ev_status == "UNKNOWN":
             # Implicitly ungrounded if no evidence found
             is_slide_grounded = False
             issues.append("No mapped claims or citations found")
        
        # 2. Constraint Checks
        # Max Lines (12)
        if len(bullets) > 12:
            issues.append(f"Too many bullets ({len(bullets)} > 12)")
        
        # Word Count (approx 15 words/bullet)
        long_bullets = [b for b in bullets if len(b.split()) > 20] # slightly lenient buffer
        if long_bullets:
            issues.append(f"{len(long_bullets)} bullets exceed word count guidelines")

        # 3. Determine Slide Status
        slide_status = VerifierStatus.PASS
        
        if not is_slide_grounded:
            if strictness == "STRICT":
                slide_status = VerifierStatus.FAIL
            elif strictness == "NORMAL":
                slide_status = VerifierStatus.WARN
            elif strictness == "DRAFT":
                # DRAFT allows ungrounded, but we note it
                slide_status = VerifierStatus.PASS
        
        # Any constraint issues make it at least WARN (unless DRAFT ignores even constraints? No, usually constraints warn)
        if issues and slide_status == VerifierStatus.PASS and strictness != "DRAFT":
             # In DRAFT, we might overlook constraint warnings or keep them as PASS with notes
             # Let's say DRAFT still warns on constraints but passes ungrounded
             if any("bullets" in i for i in issues):
                 slide_status = VerifierStatus.WARN

        slide_results.append(SlideVerifierResult(
            slide_id=slide_id,
            status=slide_status,
            missing_points=[i for i in issues if "evidence" in i or "UNGROUNDED" in i],
            notes=issues
        ))
        
        if is_slide_grounded:
            grounded_slides += 1

    # Aggregation
    coverage = (grounded_slides / total_slides * 100) if total_slides > 0 else 0.0
    
    # Determine Overall Reports Status
    if any(r.status == VerifierStatus.FAIL for r in slide_results):
        overall_status = VerifierStatus.FAIL
        blockers.append("One or more slides failed checks in STRICT mode.")
    elif any(r.status == VerifierStatus.WARN for r in slide_results):
         # If strictness is STRICT but we only have WARNs (e.g. constraints), does it FAIL? 
         # Usually strictness applies to grounding. Constraints might just be warns.
         # But in STRICT mode, maybe we want 0 warnings? 
         # MVP: FAIL on grounding in STRICT. WARN on constraints.
         overall_status = VerifierStatus.WARN
        
    # Coverage blocker check
    if strictness == "STRICT" and coverage < 100:
        overall_status = VerifierStatus.FAIL
        blockers.append(f"STRICT mode requires 100% grounding. Current: {coverage:.1f}%")
        
    return VerifierReport(
        status=overall_status,
        coverage_pct=round(coverage, 2),
        per_slide=slide_results,
        blockers=blockers,
        timestamp=datetime.datetime.now().isoformat()
    )
