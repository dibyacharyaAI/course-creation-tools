
import logging
import os

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, api_key: str = None, enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled
        if self.enabled:
             logger.info("OCR Service initialized (ENABLED).")
        else:
             logger.info("OCR Service initialized (DISABLED).")

    def extract_text(self, file_path: str) -> str:
        """
        Extracts text from a scanned PDF/Image.
        
        NOTE: This is currently a STUB / MOCK implementation.
        It does NOT connect to a real OCR backend (like DeepSeek).
        It mimics behavior by checking for specific keywords in filenames.
        """
        if not self.enabled:
            logger.info("OCR requested but service is disabled.")
            return ""

        filename = os.path.basename(file_path)
        logger.info(f"Running OCR on {filename}...")
        
        # MOCK LOGIC: Check for "scanned" in filename to simulate success
        if "scanned" in filename.lower():
            return f"[OCR EXTRACTED CONTENT FROM {filename}]\n\nThis is the text detected from the scanned document. It would normally call the DeepSeek API here."
        
        # Otherwise, assume it failed or found nothing meaningful
        logger.warning(f"OCR failed to extract significant text from {filename} (Mock).")
        return ""
