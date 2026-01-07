from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

def generate_id():
    return str(uuid.uuid4())

class GraphNode(BaseModel):
    id: str = Field(default_factory=generate_id)
    order: int = 0

class SlideNode(GraphNode):
    title: str = Field(..., description="Slide Title")
    bullets: List[str] = Field(default_factory=list, description="Content Bullets")
    speaker_notes: str = Field(default="", description="Speaker Notes")
    illustration_prompt: str = Field(default="", description="Visual Description for Image Generation")
    layout: str = Field(default="standard", description="Slide Layout Type")
    tags: Dict[str, List[str]] = Field(default_factory=dict) # e.g. {"co_ids": ["CO1"], "bloom": ["Apply"]}

class SubtopicNode(GraphNode):
    title: str
    children: List[SlideNode] = Field(default_factory=list)

class ApprovalStatus(BaseModel):
    status: str # APPROVED, REJECTED, PENDING
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    comment: Optional[str] = None

class TopicNode(GraphNode):
    title: str
    topic_id: Optional[str] = None # Legacy/Explicit ID
    outcome: Optional[str] = None # Learning Outcome
    children: List[SubtopicNode] = Field(default_factory=list)
    approval: Optional[ApprovalStatus] = None

class ModuleNode(GraphNode):
    name: str # Title
    module_id: Optional[str] = None # Legacy/Explicit ID
    ncrf_level: Optional[str] = None
    children: List[TopicNode] = Field(default_factory=list)

class ConceptNode(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class RelationEdge(BaseModel):
    source_id: str
    target_id: str
    relation_type: str  # e.g., "PREREQUISITE", "RELATED_TO"
    confidence: float = 1.0
    evidence: Optional[str] = None

class CourseGraph(BaseModel):
    course_id: int
    version: int = 1
    schema_version: int = 1 # Explicit Schema Versioning
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    children: List[ModuleNode] = Field(default_factory=list)
    concepts: List[ConceptNode] = Field(default_factory=list)
    relations: List[RelationEdge] = Field(default_factory=list)
    
    # Metadata for stats
    stats: Dict[str, Any] = Field(default_factory=dict)
