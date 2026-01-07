#!/bin/bash
set -x

HOST="http://localhost:8002"

echo "--- 1. Starting RAG Indexer (Background) ---"
pkill -f "rag-indexer" || true
sleep 1

# Enable OCR and SQLite for Mock Mode
# Using port 8002 to avoid conflicts
ENABLE_OCR=False DATABASE_URL=sqlite:///./test_rag.db PYTHONPATH=. python3 -m uvicorn services.rag-indexer.app.main:app --host 0.0.0.0 --port 8002 > server_hybrid.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 10

echo "--- 2. Create Dummy Text File ---"
echo "Hybrid search is a method that combines vector search and keyword search." > hybrid_doc.txt

echo "--- 3. Ingest File ---"
curl -X POST "$HOST/ingest" \
  -F "course_id=1000" \
  -F "file=@hybrid_doc.txt"

echo "--- 4. Search (Retrieve) ---"
# We expect hybrid_retrieve to be called.
# Since we are using MockVectorStore (due to sqlite DB URL), it should return the mock result "Mock keyword result".
# We use a dummy topic request.

curl -X POST "$HOST/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": 1000,
    "topic_ids": [{"topic_id": "t1", "topic_name": "keyword method"}]
  }' > search_results.json

echo "Response Content:"
cat search_results.json

echo "--- 5. Verify Results ---"
if grep -q "Mock keyword result" search_results.json; then
    echo "✅ Hybrid search triggered (Mock mode confirmed)."
else
    echo "❌ Hybrid search result mismatch. Check logs."
    cat server_hybrid.log
    kill $SERVER_PID
    exit 1
fi

echo "--- 6. Cleanup ---"
kill $SERVER_PID
rm hybrid_doc.txt test_rag.db
rm server_hybrid.log search_results.json
