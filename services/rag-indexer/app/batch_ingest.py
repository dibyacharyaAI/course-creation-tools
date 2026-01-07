
import os
import logging
from .indexer import Indexer

logger = logging.getLogger(__name__)

class BatchIngester:
    def __init__(self, indexer: Indexer):
        self.indexer = indexer
        
    async def ingest_directory(self, course_id: int, source_path: str, extra_metadata: dict = None):
        """
        Walk directory and ingest supported files.
        source_path: Absolute path inside container (e.g. /app/data1/catalog/courses/...)
        """
        if not os.path.exists(source_path):
            logger.error(f"Source path not found: {source_path}")
            raise FileNotFoundError(f"{source_path} does not exist")
            
        logger.info(f"Starting batch ingest for course {course_id} from {source_path}")
        
        count = 0
        for root, _, files in os.walk(source_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.pdf', '.pptx', '.txt']:
                    full_path = os.path.join(root, file)
                    # Infer scope from directory structure if possible?
                    # E.g. /module1/... 
                    # For now, simplistic flat ingest or use parent dir name as topic?
                    
                    try:
                        logger.info(f"Ingesting {file}...")
                        await self.indexer.index_file(course_id, full_path, extra_metadata=extra_metadata)
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to ingest {file}: {e}")
                        
        logger.info(f"Batch ingest complete. Processed {count} files.")
        return count
