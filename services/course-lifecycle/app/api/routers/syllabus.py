from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
import json

from ..dependencies import get_db
from ...models import SyllabusTemplate
from ...syllabus_extractor import generate_blueprint_from_text, extract_text_from_file

logger = logging.getLogger(__name__)

router = APIRouter()

class TemplateSelectRequest(BaseModel):
    template_id: str | int 

@router.get("/templates")
async def get_templates(db: Session = Depends(get_db)):
    """List available syllabus templates"""
    templates = db.query(SyllabusTemplate).all()
    # Frontend expects { id, name, program }
    return [{"id": t.id, "name": t.name, "program": t.program} for t in templates]

@router.post("/select")
async def select_template(req: TemplateSelectRequest, db: Session = Depends(get_db)):
    """Select a template and generate blueprint from it"""
    try:
        t_id = int(req.template_id)
        template = db.query(SyllabusTemplate).filter(SyllabusTemplate.id == t_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
            
        # Extract Blueprint
        blueprint = await generate_blueprint_from_text(template.content)
        if "error" in blueprint:
             raise HTTPException(status_code=500, detail=blueprint["error"])
             
        return {"blueprint": blueprint}
        
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid template ID format")
    except Exception as e:
        logger.error(f"Template selection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    """Upload syllabus file and extract blueprint"""
    try:
        content = await extract_text_from_file(file.file, file.filename)
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
            
        blueprint = await generate_blueprint_from_text(content)
        if "error" in blueprint:
             raise HTTPException(status_code=500, detail=blueprint["error"])
             
        return {"blueprint": blueprint}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
