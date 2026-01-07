#!/bin/bash
set -x

HOST="http://localhost:8001" 
# NOTE: rag-indexer usually runs on 8001 if lifecycle is 8000, 
# but need to confirm port. Docker compose usually maps ai-authoring 8000, lifecycle 8000 (different container?), 
# rag-indexer 8000? They conflict if local.
# main.py usually uses port defined in args. 
# We'll try to run rag-indexer on port 8002 to avoid conflict with lifecycle(8000).

echo "--- 1. Starting RAG Indexer (Background) ---"
pkill -f "rag-indexer" || true
sleep 1

# Enable OCR via ENV
ENABLE_OCR=True DATABASE_URL=sqlite:///./test_rag.db PYTHONPATH=. python3 -m uvicorn services.rag-indexer.app.main:app --host 0.0.0.0 --port 8002 > server_ocr.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 10

echo "--- 2. Create Mock Scanned PDF ---"
# We create a PDF that has effectively no text, but name it "scanned_doc.pdf" to trigger mock OCR
# Creating a valid PDF from CLI is hard without tools.
# Alternative: Create a text file named .pdf? PyPDF might choke.
# Better: Create a minimal valid PDF using python one-liner.
python3 -c "from pypdf import PdfWriter; w = PdfWriter(); w.add_blank_page(width=100, height=100); w.write('scanned_doc.pdf')"

echo "--- 3. Ingest File ---"
curl -X POST "http://localhost:8002/ingest" \
  -F "course_id=999" \
  -F "file=@scanned_doc.pdf"

echo "--- 4. Verify OCR Log ---"
sleep 2
if grep -q "OCR successfully added text content" server_ocr.log; then
    echo "✅ OCR Fallback triggered and success."
else
    echo "❌ OCR Not triggered or failed. Check logs."
    cat server_ocr.log
    kill $SERVER_PID
    exit 1
fi

echo "--- 5. Cleanup ---"
kill $SERVER_PID
rm scanned_doc.pdf test_rag.db
rm server_ocr.log
