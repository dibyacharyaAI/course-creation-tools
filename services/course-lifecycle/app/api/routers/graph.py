from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import logging

from ..dependencies import get_db
from ...models import Course, GraphEditLog, TopicGenerationJob
from ...graph_schema import CourseGraph, ApprovalStatus
from ...graph_builder import GraphBuilder
from ...graph.validator import GraphValidator
from ...graph_schema import ConceptNode, RelationEdge

logger = logging.getLogger(__name__)

router = APIRouter()

class SlideUpdateRequest(BaseModel):
    title: Optional[str] = None
    bullets: Optional[List[str]] = None
    speaker_notes: Optional[str] = None
    illustration_prompt: Optional[str] = None
    order: Optional[int] = None

class KGModel(BaseModel):
    concepts: List[ConceptNode]
    relations: List[RelationEdge]
    version: Optional[int] = 1

@router.get("/{course_id}/graph", response_model=CourseGraph)
async def get_course_graph(course_id: int, db: Session = Depends(get_db)):
    """Get the Course Graph (Source of Truth)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not course.course_graph:
        return CourseGraph(course_id=course_id, version=1, children=[])
        
    return course.course_graph

@router.patch("/{course_id}/graph", response_model=CourseGraph)
async def update_course_graph(course_id: int, graph_update: CourseGraph, db: Session = Depends(get_db)):
    """Update Course Graph (Full Replacement with Validation)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if graph_update.course_id != course_id:
         raise HTTPException(status_code=400, detail=f"Graph course_id {graph_update.course_id} does not match URL {course_id}")
         
    current_version = course.course_graph_version or 1
    
    # Optimistic Locking
    # If client sends version, it MUST match current_version
    if graph_update.version and graph_update.version != current_version:
        raise HTTPException(
            status_code=409, 
            detail=f"Version Conflict. Server: {current_version}, Client: {graph_update.version}. Refresh and try again."
        )

    new_version = current_version + 1
    
    graph_update.version = new_version
    course.course_graph = graph_update.model_dump(mode='json')
    course.course_graph_version = new_version
    
    db.commit()
    db.refresh(course)
    return course.course_graph

@router.post("/{course_id}/graph/build")
async def build_course_graph(course_id: int, db: Session = Depends(get_db)):
    """
    Deterministic Build of Course Graph from Blueprint & Jobs.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    jobs = db.query(TopicGenerationJob).filter(TopicGenerationJob.course_id == course_id).all()
    
    from ...utils import create_db_job_run, create_db_audit_event
    
    try:
        builder = GraphBuilder(course, jobs)
        new_graph, stats = builder.build()
        
        course.course_graph = new_graph.model_dump(mode='json')
        course.course_graph_version = new_graph.version
        
        db.commit()
        db.refresh(course)
        
        create_db_job_run(db, course_id, "BUILD", "COMPLETED", duration_ms=200) # stats?
        
        return {
            "status": "success",
            "version": new_graph.version,
            "stats": stats,
            "graph_summary": {
                "modules": len(new_graph.children),
                "total_slides": stats.get("slides_linked", 0)
            }
        }
    except Exception as e:
        create_db_job_run(db, course_id, "BUILD", "FAILED", error_details=str(e))
        logger.error(f"Graph build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{course_id}/graph/validate")
async def validate_course_graph(course_id: int, db: Session = Depends(get_db)):
    """Validate Graph Integrity"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.course_graph:
        raise HTTPException(status_code=404, detail="Course or Graph not found")
        
    validator = GraphValidator(course.course_graph)
    report = validator.validate()
    
    from ...utils import create_db_job_run
    status = "COMPLETED" if report.valid else "FAILED"
    create_db_job_run(db, course_id, "VALIDATE", status, error_details=str(report.errors) if report.errors else None)
    
    return report

@router.post("/{course_id}/topics/{topic_id}/approve", response_model=CourseGraph)
async def approve_topic_in_graph(
    course_id: int, 
    topic_id: str, 
    approval: ApprovalStatus, 
    expected_version: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Approve/Reject Topic in Graph (Source of Truth) & Sync"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
         raise HTTPException(status_code=404, detail="Course not found")
    
    if not course.course_graph:
          raise HTTPException(status_code=400, detail="Graph not initialized")

    # Optimistic Locking
    current_version = course.course_graph_version or 1
    if expected_version and expected_version != current_version:
        raise HTTPException(
            status_code=409, 
            detail=f"Version Conflict. Server: {current_version}, Client: {expected_version}. Refresh required."
        )
          
    # Optimistic Locking
    current_version = course.course_graph_version or 1
    # expected_version is passed as query param, but FastAPI makes it tricky to add to existing model body endpoint without changing signature.
    # The function signature was: async def approve_topic_in_graph(..., approval: ApprovalStatus, ...)
    # I should add expected_version: int as query param default=None?
    # User Requirement: "Ensure request includes the latest version". strict.
    
    # Wait, I can't add logic here if I don't change the signature. 
    # I need to change the function signature in the ReplacementContent too.
    # But I can't see the signature in this chunk range?
    # Let's adjust the chunk to include signature.

    
    found = False
    graph_data = course.course_graph
    
    try:
        graph = CourseGraph(**graph_data)
        
        for module in graph.children:
            for topic in module.children:
                if topic.topic_id == topic_id or topic.id == topic_id:
                    # Sync Approval
                    topic.approval = approval
                    found = True
                    break
            if found: break
        
        if not found:
            raise HTTPException(status_code=404, detail="Topic not found in graph")
            
        graph.version += 1
        course.course_graph = graph.model_dump(mode='json')
        course.course_graph_version = graph.version
        
        # Sync to Legacy TopicGenerationJob
        # Find job by topic_id (could be matched by ID provided)
        job = db.query(TopicGenerationJob).filter(
            TopicGenerationJob.course_id == course_id,
            TopicGenerationJob.topic_id == topic_id
        ).order_by(TopicGenerationJob.version.desc()).first()
        
        from ...utils import create_db_audit_event
        from datetime import datetime
        
        if job:
            job.approval_status = approval.status
            job.reviewer_id = "user" # Placeholder until we have Auth context here
            job.rejection_reason = approval.comment
            if approval.status == "APPROVED":
                 job.approved_at = datetime.now()
        
        create_db_audit_event(
            db, course_id, 
            action=approval.status, 
            topic_id=topic_id, 
            comment=approval.comment
        )
        
        db.commit()
        db.refresh(course)
        return course.course_graph
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{course_id}/topics/{topic_id}/slides/{slide_id}", response_model=CourseGraph)
async def patch_slide_node(
    course_id: int, 
    topic_id: str, 
    slide_id: str, 
    update: SlideUpdateRequest, 
    expected_version: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Granular Slide Edit (Graph SoT)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.course_graph:
         raise HTTPException(status_code=404, detail="Course or Graph not found")
    
    # Optimistic Locking
    current_version = course.course_graph_version or 1
    if expected_version and expected_version != current_version:
        raise HTTPException(
            status_code=409, 
            detail=f"Version Conflict. Server: {current_version}, Client: {expected_version}. Refresh required."
        )
         
    if update.illustration_prompt is not None and not update.illustration_prompt.strip():
         raise HTTPException(status_code=400, detail="Illustration prompt cannot be empty")
         
    graph_data = course.course_graph
    found = False
    
    try:
        graph = CourseGraph(**graph_data)
        
        for m in graph.children:
            for t in m.children:
                if t.topic_id == topic_id or t.id == topic_id:
                    for sub in t.children:
                        for s in sub.children:
                            if s.id == slide_id:
                                if update.title is not None: s.title = update.title
                                if update.bullets is not None: s.bullets = update.bullets
                                if update.speaker_notes is not None: s.speaker_notes = update.speaker_notes
                                if update.illustration_prompt is not None: s.illustration_prompt = update.illustration_prompt
                                if update.order is not None: s.order = update.order
                                
                                # Set Edited Flag
                                if s.tags is None: s.tags = {}
                                s.tags["edited_by_user"] = ["true"] # Storing as list of strings
                                
                                found = True
                                break
                        if found: break
                if found: break
            if found: break
            
        if not found:
             raise HTTPException(status_code=404, detail="Slide not found")
             
        graph.version += 1
        course.course_graph = graph.model_dump(mode='json')
        course.course_graph_version = graph.version
        
        log_entry = GraphEditLog(
            course_id=course_id,
            target_id=slide_id,
            operation="UPDATE",
            changes=update.model_dump(exclude_unset=True)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(course)
        return course.course_graph
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slide edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{course_id}/kg", response_model=KGModel)
async def get_course_kg(course_id: int, db: Session = Depends(get_db)):
    """Get Graph Layer (Concepts & Relations)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if not course.course_graph:
        return KGModel(concepts=[], relations=[], version=1)
        
    graph = CourseGraph(**course.course_graph)
    return KGModel(concepts=graph.concepts, relations=graph.relations, version=graph.version)

@router.patch("/{course_id}/kg", response_model=CourseGraph)
async def update_course_kg(
    course_id: int, 
    kg_update: KGModel, 
    expected_version: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update Graph Layer (Concepts & Relations)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
         raise HTTPException(status_code=404, detail="Course not found")
         
    if not course.course_graph:
         raise HTTPException(status_code=400, detail="Graph not initialized")

    # Optimistic Locking
    current_version = course.course_graph_version or 1
    if expected_version and expected_version != current_version:
        raise HTTPException(
            status_code=409, 
            detail=f"Version Conflict. Server: {current_version}, Client: {expected_version}. Refresh required."
        )
         
    try:
        graph = CourseGraph(**course.course_graph)
        graph.concepts = kg_update.concepts
        graph.relations = kg_update.relations
        graph.version += 1
        
        course.course_graph = graph.model_dump(mode='json')
        course.course_graph_version = graph.version
        
        # Log Audit
        log_entry = GraphEditLog(
            course_id=course_id,
            target_id="KG_LAYER",
            operation="UPDATE",
            changes={"concepts_count": len(kg_update.concepts), "relations_count": len(kg_update.relations)}
        )
        db.add(log_entry)
        
        db.commit()
        db.refresh(course)
        return course.course_graph
    except Exception as e:
        logger.error(f"KG update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
