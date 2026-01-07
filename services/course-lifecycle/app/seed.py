import json
import os
from sqlalchemy.orm import Session
from shared.core.logging import setup_logging
from shared.clients.kafka_client import KafkaClient

logger = setup_logging("CourseSeed")

def load_courses_from_json(file_path: str) -> dict:
    """Load courses from JSON file"""
    if not os.path.exists(file_path):
        logger.warning(f"Course data file not found: {file_path}")
        return {}
    
    with open(file_path, 'r') as f:
        return json.load(f)

async def seed_courses(db: Session, kafka_client: KafkaClient, data_dir: str = ""):
    # Patch for local
    if not data_dir:
         data_dir = "/app/data" if os.path.exists("/app/data") else "data"
    
    """
    Seed courses from manifest.json -> courses -> blueprint
    """
    from .models import Course
    
    manifest_path = os.path.join(data_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        logger.warning(f"Manifest not found at {manifest_path}, skipping seeding")
        return

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    courses_list = manifest.get("courses", [])
    if not courses_list:
        logger.info("No courses found in manifest for seeding")
        return
    
    seeded_count = 0
    
    for course_entry in courses_list:
        course_code = course_entry.get("course_code")
        blueprint_rel_path = course_entry.get("blueprint")
        
        # Check if course already exists
        existing = db.query(Course).filter(Course.course_code == course_code).first()
        if existing:
            logger.info(f"Course {course_code} already exists, skipping")
            continue
            
        blueprint_path = os.path.join(data_dir, blueprint_rel_path)
        if not os.path.exists(blueprint_path):
             logger.warning(f"Blueprint not found for {course_code} at {blueprint_path}")
             continue
             
        with open(blueprint_path, 'r') as f:
            bp = json.load(f)
            
        # Extract metadata from blueprint
        c_info = bp.get("course", {})
        
        # Create new course
        course = Course(
            course_code=course_code,
            title=c_info.get("course_title", course_code),
            description=c_info.get("course_objective", ""),
            programme="B.Tech", # Default or infer?
            semester=c_info.get("L-T-P", ""), # Placeholder
            obe_metadata={
                "cos": bp.get("course_outcomes", []),
                "modules": bp.get("modules", [])
            },
            blueprint=bp, # Store the full blueprint
            status="DRAFT"
        )
        
        db.add(course)
        db.commit()
        db.refresh(course)
        
        logger.info(f"✅ Seeded course: {course_code} - {course.title}")
        
        # Publish COURSE_CREATED event
        from shared.core.event_schemas import CourseCreatedPayload
        payload = CourseCreatedPayload(
            course_id=course.id,
            title=course.title,
            description=course.description or ""
        )
        await kafka_client.publish("course.events", payload.dict())
        
        seeded_count += 1
    
    logger.info(f"🎉 Seeding complete! Added {seeded_count} courses")

async def seed_templates(db: Session):
    """Seed syllabus templates using CatalogLoader"""
    from .catalog_loader import CatalogLoader
    from .models import SyllabusTemplate
    
    # Check if templates exist
    if db.query(SyllabusTemplate).count() > 0:
        logger.info("Syllabus templates already seeded, skipping")
        return

    loader = CatalogLoader() # Defaults to /app/data
    templates = loader.get_templates()
    
    count = 0
    for t in templates:
         # Need content? CatalogLoader only provides metadata unless we read file?
         # SyllabusTemplate model has 'content' field.
         # For MVP, maybe we just store dummy content or read the file?
         # Reading file might be slow if large docs.
         # But 'select' endpoint expects content to extract blueprint.
         # Ideally we lazily load, but DB model requires content?
         # Let's read the file if possible to extract text.
         # CatalogLoader uses 'extract_text_from_file' logic? No.
         
         # Let's import extraction logic if needed, OR just store path?
         # SyllabusTemplate model: content = Column(Text)
         # If we store path, 'select' endpoint needs to handle it.
         # But 'select' endpoint calls `generate_blueprint_from_text(template.content)`.
         # So we MUST store text content.
         
         # Reading all DOCX on startup might be slow.
         # For now, let's just seed the metadata and maybe lazy-load content or
         # stub it. But wait, user wants system to work!
         # I will try to read the file content.
         
         # Actually, better approach: Seed the template entry. 
         # Modify `select` endpoint to load file content if `template.content` is a file path?
         # No, keeping it simple: read valid text on startup.
         
         from .syllabus_extractor import extract_text_from_file
         full_path = loader.get_syllabus_absolute_path(t.template_id)
         content_text = ""
         
         if full_path and os.path.exists(full_path):
             try:
                # We can't use await here easily if we are in async def but extract is async?
                # extract_text_from_file is async.
                # So we can await it.
                content_text = await extract_text_from_file(full_path, full_path)
             except Exception as e:
                 logger.warning(f"Failed to read content for {t.display_label}: {e}")
                 content_text = f"Error reading file: {e}"
         else:
             content_text = "Syllabus file not found."

         db_template = SyllabusTemplate(
            name=t.display_label,
            program=t.branch,
            content=content_text 
         )
         db.add(db_template)
         count += 1
         
    db.commit()
    logger.info(f"✅ Seeded {count} syllabus templates from catalog")

