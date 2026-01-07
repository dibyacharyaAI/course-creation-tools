import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

from shared.core.settings import BaseAppSettings
from shared.core.logging import setup_logging
from .pdf_generator import PDFGenerator
from .pptx_generator import PPTXGenerator

class Settings(BaseAppSettings):
    APP_NAME: str = "Exporter Service"

settings = Settings()
logger = setup_logging(settings.APP_NAME)

app = FastAPI(title=settings.APP_NAME)

# Database Setup (Read-only access to fetch course content)
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Generators
pdf_gen = PDFGenerator()
pptx_gen = PPTXGenerator()

class ExportRequest(BaseModel):
    variant: str = "student" # student, teacher

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}

def get_course_data(course_id: int):
    with SessionLocal() as db:
        result = db.execute(
            text("SELECT id, title, description, course_code, programme, semester, obe_metadata, content FROM courses WHERE id = :id"),
            {"id": course_id}
        ).fetchone()
        
        if not result:
            return None
            
        return {
            "id": result.id,
            "title": result.title,
            "description": result.description,
            "course_code": result.course_code,
            "programme": result.programme,
            "semester": result.semester,
            "obe_metadata": result.obe_metadata,
            "content": result.content
        }

@app.post("/courses/{course_id}/export/pdf")
async def export_pdf(course_id: int, request: ExportRequest):
    course_data = get_course_data(course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not course_data.get('content'):
        raise HTTPException(status_code=400, detail="Course content not ready yet")
        
    try:
        filename = pdf_gen.generate_student_notes(course_data)
        return {
            "status": "READY",
            "format": "pdf",
            "download_url": f"/exports/{filename}"
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/courses/{course_id}/export/pptx")
async def export_pptx(course_id: int, request: ExportRequest):
    course_data = get_course_data(course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not course_data.get('content'):
        raise HTTPException(status_code=400, detail="Course content not ready yet")
        
    try:
        filename = pptx_gen.generate_slides(course_data)
        return {
            "status": "READY",
            "format": "pptx",
            "download_url": f"/exports/{filename}"
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exports/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("/app/exports", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)
