from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from ..graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode

class ValidationIssue(BaseModel):
    type: str # ERROR or WARNING
    message: str
    target_id: str # Topic ID or Slide ID
    location: str # "Topic {id}" or "Slide {id} in Topic {id}"

class ValidationReport(BaseModel):
    valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)

class GraphValidator:
    def __init__(self, course_graph: Dict[str, Any]):
        self.graph = CourseGraph(**course_graph)
        
    def validate(self) -> ValidationReport:
        report = ValidationReport(valid=True)
        
        for module in self.graph.children:
            for topic in module.children:
                self._validate_topic_logic(topic, report)
                
        if report.errors:
            report.valid = False
            
        return report

    def validate_topic(self, topic: TopicNode) -> ValidationReport:
        report = ValidationReport(valid=True)
        self._validate_topic_logic(topic, report)
        if report.errors: report.valid = False
        return report

    def _validate_topic_logic(self, topic: TopicNode, report: ValidationReport):
        topic_id = topic.topic_id or topic.id
        slide_count = 0
        seen_orders = set()
        
        for subtopic in topic.children:
            for slide in subtopic.children:
                slide_count += 1
                self._validate_slide(slide, topic_id, report)
                
                # Check Order Uniqueness
                if slide.order in seen_orders:
                    report.errors.append(ValidationIssue(
                        type="ERROR",
                        message=f"Duplicate slide order {slide.order} found.",
                        target_id=slide.id,
                        location=f"Slide {slide.order} in Topic {topic.title}"
                    ))
                seen_orders.add(slide.order)
                
        # Rule: Slide Count (Target 8, tolerance 6-10)
        if slide_count < 6 or slide_count > 10:
             report.errors.append(ValidationIssue(
                type="ERROR",
                message=f"Topic has {slide_count} slides (must be 6-10).",
                target_id=topic_id,
                location=f"Topic {topic.title}"
            ))
        elif slide_count != 8:
             report.warnings.append(ValidationIssue(
                type="WARNING",
                message=f"Topic has {slide_count} slides (target is 8).",
                target_id=topic_id,
                location=f"Topic {topic.title}"
            ))

    def _validate_slide(self, slide: SlideNode, topic_id: str, report: ValidationReport):
        # Rule: Non-empty title
        if not slide.title or not slide.title.strip():
             report.errors.append(ValidationIssue(
                type="ERROR",
                message="Slide missing title.",
                target_id=slide.id,
                location=f"Slide {slide.id} in Topic {topic_id}"
            ))
            
        # Rule: >= 1 bullet (Error), 3-5 recommended (Warning)
        b_len = len(slide.bullets) if slide.bullets else 0
        if b_len == 0:
             report.errors.append(ValidationIssue(
                type="ERROR",
                message="Slide must have at least one bullet point.",
                target_id=slide.id,
                location=f"Slide {slide.id} in Topic {topic_id}"
            ))
        elif b_len < 3 or b_len > 5:
             report.warnings.append(ValidationIssue(
                type="WARNING",
                message=f"Slide has {b_len} bullets (recommended 3-5).",
                target_id=slide.id,
                location=f"Slide {slide.id} in Topic {topic_id}"
            ))
            
        # Rule: Illustration prompt non-empty
        if not slide.illustration_prompt or not slide.illustration_prompt.strip():
             report.errors.append(ValidationIssue(
                type="ERROR",
                message="Slide missing illustration prompt.",
                target_id=slide.id,
                location=f"Slide {slide.id} in Topic {topic_id}"
            ))
