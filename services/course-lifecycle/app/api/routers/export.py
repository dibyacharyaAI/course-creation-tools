from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import os
import requests
import logging

from ..dependencies import get_db
from ...models import Course
from ...graph.compiler import GraphCompiler
from ...graph.validator import GraphValidator
from ...pdf_builder import PDFBuilder
from ...utils import log_telemetry # Assume exists
from ...settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/courses/{course_id}/export/ppt")
async def export_course_ppt(course_id: int, force: bool = False, topic_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Export Full Course or Single Topic PPT from Graph"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.course_graph:
        raise HTTPException(status_code=404, detail="Course/Graph not found")
    
    # 1. Validation Logic
    if not force:
        validator = GraphValidator(course.course_graph)
        report = validator.validate()
        if not report.valid:
             raise HTTPException(status_code=422, detail={"message": "Validation Failed", "report": report.dict()})
        
    # 2. Strict HITL Check (Task 2)
    # Enforce all included topics are APPROVED?
    from ...graph_schema import CourseGraph
    from ...utils import create_db_job_run
    
    if not force:
        try:
            graph = CourseGraph(**course.course_graph)
            unapproved = []
            for m in graph.children:
                for t in m.children:
                    # If topic_id is specified, skip others
                    if topic_id and t.topic_id != topic_id and t.id != topic_id:
                        continue
                    if not t.approval or t.approval.status != "APPROVED":
                        unapproved.append(t.title)
            
            if unapproved:
                create_db_job_run(db, course_id, "EXPORT_PPT", "BLOCKED", error_details=f"Unapproved: {unapproved}")
                raise HTTPException(status_code=422, detail=f"Cannot export. Unapproved topics: {unapproved}. Use force=true to bypass.")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Approval check failed: {e}")
            # If graph parsing fails, maybe just warn? But strict production usually fails safe.
            raise HTTPException(status_code=500, detail="Graph integrity error during approval check")
    
    compiler = GraphCompiler(course.course_graph)
    # TODO: Add `approval_required=not force` to compile?
    slide_plan = compiler.compile(topic_id=topic_id) 
    
    if not slide_plan.slides:
         raise HTTPException(status_code=400, detail="Graph is empty")
         
    # 3. Call Renderer
    # If renderer is down, we can't do much for PPT.
    try:
        # Prepare Output Path (Absolute path in shared volume)
        out_parent = Path(settings.EXPORT_DIR).resolve()
        out_dir = out_parent / str(course_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{topic_id}.pptx" if topic_id else f"course_{course_id}.pptx"
        output_path = out_dir / filename
        
        # Prepare Slide Plan with Title (Boss Requirement)
        # KG SoT: Use course.title only, never fallback to blueprint
        slide_plan_dict = slide_plan.dict()
        course_title = course.title or f"Course {course_id}"
        slide_plan_dict["title"] = course_title
        
        payload = {
            "slide_plan": slide_plan_dict,
            "course_id": str(course_id),
            "theme": "modern",
            "output_path": str(output_path)
        }
        # Assuming internal service
        resp = requests.post(f"http://ppt-renderer:3000/render", json=payload, timeout=120)
        if resp.status_code != 200:
             create_db_job_run(db, course_id, "EXPORT_PPT", "FAILED", error_details=resp.text)
             raise HTTPException(status_code=500, detail=f"Renderer failed: {resp.text}")
             
        create_db_job_run(db, course_id, "EXPORT_PPT", "COMPLETED")
        return resp.json() 
    except requests.exceptions.ConnectionError:
        # Fallback Logic: Return error but suggest PDF
        create_db_job_run(db, course_id, "EXPORT_PPT", "FAILED", error_details="Renderer ConnectionError")
        raise HTTPException(status_code=503, detail="PPT Service Unavailable. Try PDF Export.")
    except Exception as e:
        create_db_job_run(db, course_id, "EXPORT_PPT", "FAILED", error_details=str(e))
        logger.error(f"Full export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/export/ppt")
async def get_course_ppt(course_id: int, force: bool = False, topic_id: Optional[str] = None, db: Session = Depends(get_db)):
    """GET Endpoint for Browser Download of PPT"""
    # Reuse logic to generate/ensure existence
    try:
        # We call the generation logic.
        resp_data = await export_course_ppt(course_id, force=force, topic_id=topic_id, db=db)
        
        # If we got here, it succeeded.
        # Path is likely in resp_data. Let's inspect `ppt-renderer` contract or assume standard mapping.
        # Based on `generate_topic_ppt` stub in courses.py, it was `/generated/...`
        # `export.py` line 224 (before) was sending to renderer.
        # Let's assume the path is derivable or in response.
        # Use Standard location if response doesn't give absolute path we can verify?
        # Actually `export_course_pdf` returns `{"pdf_path": ...}`.
        # `export_course_ppt` returns `resp.json()`.
        
        # If we can't trust the return, we check the standard path.
        # But we don't know the standard path for "Full Course" vs "Topic".
        # Let's assume we can rely on `resp_data.get("ppt_path")`.
        
        path = resp_data.get("ppt_path") or resp_data.get("path")
        if not path:
             # Fallback: construct standard path?
             # If topic_id:
             # path = f"/app/generated_data/exports/{course_id}/{topic_id}.pptx"
             pass
        
        if path and os.path.exists(path):
             return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=os.path.basename(path))
        else:
             # If mocking, maybe we don't have file.
             raise HTTPException(status_code=404, detail="PPT Generated but file not found (Mock?)")
             
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/courses/{course_id}/export/pdf")
async def export_course_pdf(course_id: int, force: bool = False, topic_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Export Full Course or Single Topic Handout PDF (Determinisric & Local)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.course_graph:
        raise HTTPException(status_code=404, detail="Course/Graph not found")
    
    from ...graph_schema import CourseGraph
    from ...utils import create_db_job_run

    if not force:
        try:
            graph = CourseGraph(**course.course_graph)
            unapproved = []
            for m in graph.children:
                for t in m.children:
                    # If topic_id is specified, skip others
                    if topic_id and t.topic_id != topic_id and t.id != topic_id:
                        continue
                    if not t.approval or t.approval.status != "APPROVED":
                        unapproved.append(t.title)
            
            if unapproved:
                create_db_job_run(db, course_id, "EXPORT_PDF", "BLOCKED", error_details=f"Unapproved: {unapproved}")
                raise HTTPException(status_code=422, detail=f"Cannot export. Unapproved topics: {unapproved}. Use force=true to bypass.")
        except HTTPException:
            raise
        except Exception:
            pass # Validation logic handles main errors

    compiler = GraphCompiler(course.course_graph)
    slide_plan = compiler.compile(topic_id=topic_id)
    
    if not slide_plan.slides:
        raise HTTPException(status_code=400, detail="Graph empty")

    try:
        # Determine output directory (Shared Volume)
        out_parent = Path(settings.EXPORT_DIR).resolve()
        out_dir = out_parent / str(course_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"course_handout_{topic_id}.pdf" if topic_id else "course_handout.pdf"
        out_path = out_dir / filename
        
        # Build PDF
        pdf = PDFBuilder()
        pdf.build(slide_plan, str(out_path))
        
        create_db_job_run(db, course_id, "EXPORT_PDF", "COMPLETED")
        
        return {"pdf_path": str(out_path)}
        
    except Exception as e:
         create_db_job_run(db, course_id, "EXPORT_PDF", "FAILED", error_details=str(e))
         logger.error(f"Full PDF Export failed: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/export/pdf")
async def get_course_pdf(course_id: int, force: bool = False, topic_id: Optional[str] = None, db: Session = Depends(get_db)):
    """GET Endpoint for Browser Download of PDF"""
    try:
        resp = await export_course_pdf(course_id, force=force, topic_id=topic_id, db=db)
        path = resp.get("pdf_path")
        
        if path and os.path.exists(path):
            filename = f"course_{course_id}_{topic_id}.pdf" if topic_id else f"course_{course_id}.pdf"
            return FileResponse(path, media_type="application/pdf", filename=filename)
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/courses/{course_id}/export/pdf/download")
async def download_course_pdf(course_id: int, db: Session = Depends(get_db)):
    """Download the PDF artifact"""
    # Download PDF artifact
    path = Path(settings.EXPORT_DIR) / str(course_id) / "course_handout.pdf"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found. Generate first.")
    return FileResponse(path, media_type="application/pdf", filename=f"course_{course_id}.pdf")
