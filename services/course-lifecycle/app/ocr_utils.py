import fitz  # PyMuPDF
import logging
from .settings import settings

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_bytes: bytes, filename: str) -> str:
    """
    Extracts text from PDF bytes.
    Detects if OCR is needed (scanned document) and runs it if enabled.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        total_pages = len(doc)
        scanned_pages = 0
        
        for page in doc:
            text = page.get_text()
            full_text += text
            
            # Simple heuristic: If page has images but very little text, it might be scanned.
            # < 50 chars per page is suspicious for a full page doc
            if len(text.strip()) < 50:
                 scanned_pages += 1

        is_likely_scanned = (scanned_pages / total_pages) > 0.5 if total_pages > 0 else False
        
        if is_likely_scanned:
            logger.info(f"PDF {filename} appears to be scanned ({scanned_pages}/{total_pages} low-text pages).")
            
            if settings.ENABLE_OCR:
                logger.info("OCR Enabled. Attempting deep OCR...")
                ocr_text = _run_ocr_stub(file_bytes)
                if ocr_text:
                    return ocr_text
            else:
                logger.warning(f"OCR Disabled. Skipping OCR for scanned doc {filename}. Text extraction may be poor.")
        
        return full_text

    except Exception as e:
        logger.error(f"Text extraction failed for {filename}: {e}")
        return ""

def _run_ocr_stub(file_bytes: bytes) -> str:
    """
    Real OCR Integration.
    Calls external OCR service via HTTP if configured.
    """
    if not settings.OCR_SERVICE_URL:
        logger.warning("OCR Enabled but OCR_SERVICE_URL not set. Falling back to simulated output.")
        return "DeepSeek-OCR Result (Simulation): OCR Configured but URL missing."
        
    logger.info(f"Calling DeepSeek-OCR Service at {settings.OCR_SERVICE_URL}...")
    import httpx
    
    try:
        # Assuming OCR service expects multipart file upload
        files = {'file': ('document.pdf', file_bytes, 'application/pdf')}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{settings.OCR_SERVICE_URL}/ocr/pdf", files=files)
            resp.raise_for_status()
            
            data = resp.json()
            ocr_text = data.get("text", "")
            logger.info(f"OCR Success. Extracted {len(ocr_text)} characters.")
            return ocr_text
            
    except Exception as e:
        logger.error(f"OCR Service Call Failed: {e}")
        return "" # Fallback to empty (caller uses standard text extraction)
