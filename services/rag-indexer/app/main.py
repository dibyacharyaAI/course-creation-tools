import asyncio
import logging
import shutil
import os
from typing import List, Dict, Any, Optional # Added imports
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from shared.core.settings import BaseAppSettings
from shared.core.logging import setup_logging
from shared.clients.kafka_client import KafkaClient
from .indexer import Indexer

class Settings(BaseAppSettings):
    APP_NAME: str = "RAG Indexer Service"
    DATA_PACK_ROOT: str = "/app/data"
    ENABLE_OCR: bool = False
    DEEPSEEK_API_KEY: Optional[str] = None

settings = Settings()
logger = setup_logging(settings.APP_NAME)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# Initialize Kafka Client
kafka_client = KafkaClient(settings.KAFKA_BOOTSTRAP_SERVERS, settings.APP_NAME)

# Initialize Indexer
indexer = Indexer(
    api_key=settings.GEMINI_API_KEY, 
    database_url=settings.DATABASE_URL,
    ocr_enabled=settings.ENABLE_OCR,
    deepseek_api_key=settings.DEEPSEEK_API_KEY
)

@app.on_event("startup")
async def startup_event():
    # Start consumer in background
    asyncio.create_task(kafka_client.start_consumer(
        topics=["course.events"],
        callback=process_event,
        group_id="rag-indexer-group"
    ))
    logger.info("🚀 RAG Indexer Service started")

@app.on_event("shutdown")
async def shutdown_event():
    await kafka_client.stop()

async def process_event(topic: str, message: dict):
    """
    Process incoming Kafka events.
    Handles:
    - COURSE_CREATED: Index course syllabus/summary
    - CONTENT_READY_FOR_INDEXING (or inference from content update): Index generated content
    """
    try:
        if "content" in message:
            # Check if it's content ready for indexing
            # message structure depends on payload. 
            # ContentReadyForIndexingPayload has 'content' dict.
            # CourseCreatedPayload has title/desc.
            
            course_id = message.get("course_id")
            
            # Simple heuristic: if it has 'modules' in content, it's full content
            content = message.get("content", {})
            if isinstance(content, dict) and "modules" in content:
                logger.info(f"📥 Received content for indexing: Course {course_id}")
                await indexer.index_course_content(course_id, content)
            
        elif "title" in message and "description" in message:
             # Course Created Event
             course_id = message.get("course_id")
             title = message.get("title")
             description = message.get("description")
             
             logger.info(f"📥 Received new course for indexing: {title}")
             await indexer.index_course_metadata(course_id, title, description)
             
    except Exception as e:
        logger.error(f"Error processing event: {e}")

@app.post("/ingest")
async def ingest_file(
    course_id: int = Form(...),
    module_id: str = Form(None),
    topic_id: str = Form(None),
    file: UploadFile = File(...)
):
    """
    Ingest a custom file for RAG indexing.
    """
    if not settings.GEMINI_API_KEY:
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot ingest.")
         
    try:
        temp_dir = "/tmp/ingest"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Received file upload: {file.filename} for course {course_id}")
        
        await indexer.index_file(course_id, file_path, module_id, topic_id)
        
        os.remove(file_path)
        return {"status": "indexed", "filename": file.filename, "course_id": course_id}
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return {"status": "error", "message": str(e)}

from .batch_ingest import BatchIngester

# ...
batch_ingester = BatchIngester(indexer)

class BatchIngestRequest(BaseModel):
    course_id: int
    data1_path: str # e.g. "catalog/courses/XCT3002/materials"

@app.post("/ingest/batch")
async def ingest_batch(req: BatchIngestRequest):
    """Trigger batch ingestion from data1"""
    # Sanitize path to ensure it stays in /app/data1
    base_path = "/app/data"
    target_path = os.path.join(base_path, req.data1_path.strip("/"))
    
    if not target_path.startswith(base_path):
         raise HTTPException(status_code=400, detail="Invalid path")
         
    if not settings.GEMINI_API_KEY:
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot batch ingest.")

    try:
        count = await batch_ingester.ingest_directory(req.course_id, target_path)
        return {"status": "success", "files_ingested": count}
    except Exception as e:
        logger.error(f"Batch ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}

@app.post("/reference/ingest")
async def ingest_reference(
    course_id: int = Form(...),
    course_code: str = Form(None),
    blueprint_id: str = Form(None),
    scope_level: str = Form("course"), # course, module, topic
    module_id: str = Form(None),
    topic_id: str = Form(None),
    use_packaged: bool = Form(False),
    files: list[UploadFile] = File(None)
):
    """
    Ingest reference materials (packaged or uploaded) with strict scoping.
    """
    if not settings.GEMINI_API_KEY:
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot ingest references.")

    try:
        # Validate Scope
        if scope_level == "module" and not module_id:
             raise HTTPException(status_code=400, detail="module_id required for module scope")
        if scope_level == "topic" and (not module_id or not topic_id):
             raise HTTPException(status_code=400, detail="module_id and topic_id required for topic scope")

        extra_metadata = {
            "scope_level": scope_level,
            "module_id": module_id,
            "topic_id": topic_id
        }
        if blueprint_id:
            extra_metadata["blueprint_id"] = blueprint_id
            
        ingested_count = 0
        
        # 1. Handle Packaged References
        if use_packaged:
            if not course_code:
                raise HTTPException(status_code=400, detail="course_code required for packaged references")
                
            package_path = os.path.join(settings.DATA_PACK_ROOT, "catalog", "courses", course_code, "materials")
            
            logger.info(f"Ingesting packaged references from {package_path} with scope {scope_level}")
            if os.path.exists(package_path):
                # We assume packaged refs are generally Course Level unless organized by folder, 
                # but for now we apply the user-selected scope to all of them if they asked.
                count = await batch_ingester.ingest_directory(course_id, package_path, extra_metadata=extra_metadata)
                ingested_count += count
            else:
                 # It's not an error if missing, just zero found. But warn.
                logger.warning(f"Packaged path not found: {package_path}")
                # We return 0 instead of error to avoid blocking UI
        
        # 2. Handle Uploaded Files
        if files:
            temp_dir = "/tmp/ingest_refs"
            os.makedirs(temp_dir, exist_ok=True)
            
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    
                logger.info(f"Ingesting uploaded reference: {file.filename}")
                await indexer.index_file(course_id, file_path, extra_metadata=extra_metadata)
                os.remove(file_path)
                ingested_count += 1
                
        return {"status": "success", "ingested_count": ingested_count, "course_id": course_id}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Reference ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
class TopicRequest(BaseModel):
    topic_id: str
    topic_name: str

class RetrieveRequest(BaseModel):
    course_id: int
    topic_ids: List[TopicRequest]
    k: int = 3

@app.post("/retrieve")
async def retrieve_evidence(req: RetrieveRequest):
    """
    Retrieve evidence for a list of topics.
    """
    if not settings.GEMINI_API_KEY:
         raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured. Cannot retrieve.")

    results_map = {}
    for topic in req.topic_ids:
        tid = topic.topic_id
        tname = topic.topic_name
        
        # Search using topic name as query
        raw_results = await indexer.hybrid_retrieve(req.course_id, tname, k=req.k)
        
        # Transform to EvidenceItem structure (simplified for transport)
        evidence_items = []
        for res in raw_results:
            meta = res.get("metadata", {})
            evidence_items.append({
                "source_id": meta.get("filename") or meta.get("source") or "unknown",
                "locator": meta.get("page_number") or meta.get("locator") or "unknown",
                "snippet": res.get("content", "")[:500], # Truncate for now
                "score": res.get("score", 0),
                "metadata": meta
            })
            
        results_map[tid] = evidence_items
        
    return results_map
