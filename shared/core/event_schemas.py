from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class CourseCreatedPayload(BaseModel):
    course_id: int
    title: str
    description: str

class ContentGeneratedPayload(BaseModel):
    course_id: int
    content: Dict[str, Any]  # JSON structure of the generated course

class ContentReadyForIndexingPayload(BaseModel):
    course_id: int
    course_code: Optional[str] = None
    content: Dict[str, Any]


class BlueprintReadyPayload(BaseModel):
    course_id: int
    blueprint: Dict[str, Any]

class GenerationRequestedPayload(BaseModel):
    course_id: int
    blueprint: Dict[str, Any]
    generation_spec: Dict[str, Any]
    prompt_text: str
    scope: Optional[Dict[str, Any]] = None # {module_id: ..., topic_id: ...}

class PPTRequestedPayload(BaseModel):
    course_id: int
    blueprint: Dict[str, Any]
    generation_spec: Dict[str, Any]
    prompt_text: str

class PPTGeneratedPayload(BaseModel):
    course_id: int
    slide_plan: Dict[str, Any]
    ppt_artifact: Optional[Dict[str, Any]] = None # {path: ..., url: ...}

class FullContentRequestedPayload(BaseModel):
    course_id: int
    slide_plan: Dict[str, Any]
    output_formats: List[str]
