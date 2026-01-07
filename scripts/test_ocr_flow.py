import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock

# Add service path to sys.path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'services/rag-indexer'))

# Mock pypdf and pptx if needed, or rely on them being installed in env (they might not be in the agent env)
# The agent env usually has basic libs. If pypdf is missing, we might need to mock it.
# Let's try to mock PdfReader to avoid dependency issues in this test script environment.
sys.modules['pypdf'] = MagicMock()
sys.modules['pypdf.PdfReader'] = MagicMock()
sys.modules['pptx'] = MagicMock()

# Mock shared clients
sys.modules['shared'] = MagicMock()
sys.modules['shared.clients'] = MagicMock()
sys.modules['shared.clients.embedding_client'] = MagicMock()
sys.modules['shared.clients.vector_store_client'] = MagicMock()

# Now import the actual app modules
# We need to hack the import because 'services/rag-indexer' is not a valid python package name with hyphen usually, 
# but if we added the path, we can import 'app.indexer'.
try:
    from app.ocr_service import OCRService
    from app.indexer import Indexer
except ImportError:
    # Fallback layout
    sys.path.append(os.path.join(os.getcwd(), 'services/rag-indexer/app'))
    from ocr_service import OCRService
    from indexer import Indexer

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr_test")

class MockPdfReader:
    def __init__(self, path):
        self.pages = [MagicMock()]
        self.pages[0].extract_text.return_value = "   " # Simulate empty/scanned text

def run_test():
    logger.info("--- Starting OCR Flow Verification ---")
    
    # 1. Test OCR Service Logic
    logger.info("1. Testing OCRService Stub...")
    ocr = OCRService(enabled=True)
    
    # Test Scanned
    res = ocr.extract_text("path/to/scanned_doc.pdf")
    if "[OCR EXTRACTED CONTENT" in res:
        logger.info("✅ OCR Service handled 'scanned' filename correctly.")
    else:
        logger.error(f"❌ OCR Service failed 'scanned' test. Got: {res}")
        
    # Test Normal
    res = ocr.extract_text("path/to/normal.pdf")
    if res == "":
        logger.info("✅ OCR Service handled 'normal' filename correctly (mock logic).")
    else:
        logger.error(f"❌ OCR Service failed 'normal' test. Got: {res}")

    # 2. Test Integration in Indexer
    logger.info("2. Testing Indexer Integration...")
    
    # Mock mocks
    sys.modules['pypdf'].PdfReader = MockPdfReader
    
    indexer = Indexer(
        api_key="dummy", 
        database_url="sqlite:///:memory:", 
        ocr_enabled=True
    )
    
    # Mock Vector Store add_documents to verify it was called
    indexer.vector_store.add_documents = MagicMock()
    indexer.vector_store.add_documents = MagicMock()
    
    async def mock_embed_batch(x):
        return [MagicMock(embedding=[0.1]*768)] * len(x)
        
    indexer.embedding_client.embed_batch = mock_embed_batch
    
    # Create dummy pdf file (needed for os.path.exists checks if any? Code uses open for txt, but PdfReader for pdf)
    # The code: reader = PdfReader(file_path). 
    # Our mock replaces PdfReader so file existence doesn't matter for the reader, 
    # BUT python might check it? No, PdfReader(str) just passes str.
    
    test_file = "test_scanned.pdf"
    
    # Run Indexing
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(indexer.index_file(101, test_file))
        
        # Verify OCR was called
        # We can't spy on the internal ocr_service easily without mocking it before init, 
        # but we can check the LOGS or the CONTENT sent to vector store.
        
        calls = indexer.vector_store.add_documents.call_args
        if calls:
            args, _ = calls
            texts = args[0]
            start_text = texts[0]
            logger.info(f"Indexed Text Start: {start_text[:50]}...")
            if "[OCR EXTRACTED" in start_text:
                logger.info("✅ Indexer correctly fell back to OCR and included text.")
            else:
                 logger.error("❌ Indexer did NOT include OCR text.")
        else:
             logger.error("❌ vector_store.add_documents was never called.")

    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")

if __name__ == "__main__":
    run_test()
