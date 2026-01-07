from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Literal, Any
from enum import Enum
import math

# --- 1. Evidence Models ---

class EvidenceSourceType(str, Enum):
    BLUEPRINT = "blueprint"
    REFERENCE_TEXT = "reference_text"
    KNOWLEDGE_BASE = "knowledge_base"

class EvidenceItem(BaseModel):
    source_id: str = Field(..., description="Unique ID of the source (e.g. filename, topic_id)")
    source_type: EvidenceSourceType
    locator: Optional[str] = Field(None, description="Page number, slide ID, or section header")
    snippet: Optional[str] = Field(None, description="Exact text quoted from source")
    support_strength: Literal["STRONG", "WEAK", "INFERRED"] = "STRONG"

class ClaimEvidence(BaseModel):
    claim_id: str
    claim_text: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    grounding_status: Literal["GROUNDED", "UNSUPPORTED", "PARTIAL"] = "UNSUPPORTED"
    uncertainty_notes: Optional[str] = None

class SlideEvidenceMap(BaseModel):
    bullets: Dict[str, ClaimEvidence] = Field(default_factory=dict, description="Map of bullet_index/id to evidence")
    slide_level_evidence: List[EvidenceItem] = Field(default_factory=list)

class EvidenceMap(BaseModel):
    # Key is slide_id (S1, S2...)
    # Key is slide_id (S1, S2...)
    slides: Dict[str, SlideEvidenceMap] = Field(default_factory=dict)

class SlideContent(BaseModel):
    id: str
    title: str
    bullets: List[str]
    speaker_notes: Optional[str] = None
    illustration_prompt: Optional[str] = None
    topic_id: Optional[str] = None
    subtopic_id: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict) # MO/CO/Bloom/NCRF

class SlideStructure(BaseModel):
    slides: List[SlideContent]

class ContentGenerationRequest(BaseModel):
    output_formats: List[str] = Field(default_factory=lambda: ["zip"])

class GenerationRequest(BaseModel):
    course_id: Optional[int] = None
    blueprint: Dict[str, Any]
    generation_spec: Dict[str, Any]
    prompt_text: str
    scope: Optional[Dict[str, Any]] = None
    bloom: Optional[str] = None


# --- 2. Verifier Models ---

class VerifierStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"

class SlideVerifierResult(BaseModel):
    slide_id: str
    status: VerifierStatus
    missing_points: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

class VerifierReport(BaseModel):
    status: VerifierStatus
    coverage_pct: float
    per_slide: List[SlideVerifierResult] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = None


# --- 3. Client Course Models (Canonical) ---

class Credits(BaseModel):
    l: int = Field(ge=0)
    t: int = Field(ge=0)
    p: int = Field(ge=0)
    total: int = Field(ge=1)

    @model_validator(mode='after')
    def check_total(self) -> 'Credits':
        # Typically total = L + T + P/2 or similar, but here we just ensure basic sanity
        # Ensure calculated total roughly matches provided total if stricter logic needed?
        # For now, just ensure at least one component is > 0
        if self.l + self.t + self.p == 0:
            raise ValueError("Course must have at least some L/T/P hours")
        return self

class CourseIdentity(BaseModel):
    program: str
    course_code: str
    course_title: str
    credits: Credits
    ncrf_level: Optional[str] = None
    category: Optional[str] = None

class CourseOutcome(BaseModel):
    id: str
    description: str
    bloom_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    ncrf_level: Optional[str] = None
    employability: Optional[str] = None

class ModuleOutcome(BaseModel):
    id: str
    title: str
    topics: List[str]
    bloom_level: Optional[str] = None
    employability: Optional[str] = None

class Module(BaseModel):
    id: str
    title: str
    ncrf_level: Optional[str] = None
    mos: List[ModuleOutcome]
    mo_co_map: List[List[int]] = Field(default_factory=list, description="Matrix of MO x CO mapping strength (0-3)")

class TimeDistribution(BaseModel):
    module_weights: List[float]

    @field_validator('module_weights')
    @classmethod
    def check_weights_sum(cls, v: List[float]) -> List[float]:
        if not v:
            return v
        total = sum(v)
        if not math.isclose(total, 1.0, rel_tol=1e-2):
           raise ValueError(f"Module weights sum to {total}, must be approx 1.0")
        return v

class ClientCourse(BaseModel):
    """
    Canonical source-of-truth for course data structure as per client spec.
    """
    course_identity: CourseIdentity
    pos: List[str] = Field(..., min_length=12, max_length=12, description="Program Outcomes (12)")
    cos: List[CourseOutcome] = Field(..., min_length=4, max_length=6, description="Course Outcomes (4-6)")
    
    co_po_map: List[List[int]] = Field(..., description="Matrix CO x PO mapping strength (0-3)")
    
    modules: List[Module]
    time_distribution: TimeDistribution

    @model_validator(mode='after')
    def validate_matrices_and_counts(self) -> 'ClientCourse':
        num_cos = len(self.cos)
        num_pos = len(self.pos)
        num_modules = len(self.modules)

        # 1. Validate CO-PO Matrix dimensions
        if len(self.co_po_map) != num_cos:
            raise ValueError(f"CO-PO matrix rows ({len(self.co_po_map)}) must match CO count ({num_cos})")
        
        for idx, row in enumerate(self.co_po_map):
            if len(row) != num_pos:
                raise ValueError(f"CO-PO matrix row {idx} length ({len(row)}) must match PO count ({num_pos})")
            if any(val not in [0, 1, 2, 3] for val in row):
                 raise ValueError(f"CO-PO matrix values must be 0, 1, 2, or 3. Found invalid in row {idx}")

        # 2. Validate Module Weights Count
        if len(self.time_distribution.module_weights) != num_modules:
             raise ValueError(f"Time distribution weights count ({len(self.time_distribution.module_weights)}) must match Module count ({num_modules})")

        # 3. Validate MO-CO Matrix inside modules
        for m_idx, module in enumerate(self.modules):
            num_mos = len(module.mos)
            # mo_co_map is MO x CO
            if len(module.mo_co_map) != num_mos:
                raise ValueError(f"Module {module.id}: MO-CO matrix rows ({len(module.mo_co_map)}) must match MO count ({num_mos})")
            
            for r_idx, row in enumerate(module.mo_co_map):
                if len(row) != num_cos:
                    raise ValueError(f"Module {module.id}: MO-CO matrix row {r_idx} length ({len(row)}) must match CO count ({num_cos})")
                if any(val not in [0, 1, 2, 3] for val in row):
                    raise ValueError(f"Module {module.id}: MO-CO matrix values must be 0, 1, 2, or 3.")

        return self
