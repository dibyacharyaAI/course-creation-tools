#!/bin/bash
set -x
set -e

HOST="http://localhost:8000"

echo "--- 1. Resetting DB ---"
rm test.db || true

echo "--- 2. Starting Server (Background) ---"
# Kill any existing server
pkill -f uvicorn || true
sleep 2

DATABASE_URL=sqlite:///./test.db PYTHONPATH=. uvicorn services.course-lifecycle.app.main:app --host 0.0.0.0 --port 8000 > server_content.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 15

echo "--- 3. Creating Course ---"
COURSE_PAYLOAD='{
  "title": "Content Bundle Demo",
  "program_name": "B.Tech",
  "course_code": "BUNDLE101"
}'
curl -X POST "$HOST/courses" \
  -H "Content-Type: application/json" \
  -d "$COURSE_PAYLOAD"

COURSE_ID=1
TOPIC_ID="T_BUNDLE_1"

echo "--- 4. Trigger Topic Generation ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate" \
  -H "Content-Type: application/json" -d '{}'

echo "--- 5. Verify Topic (Mock forces > 8 slides) ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/verify" \
  -H "Content-Type: application/json" -d '{}'

echo "--- 6. Approve Topic ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/approve" \
  -H "Content-Type: application/json" -d '{"notes": "Looks good"}'

echo "--- 7. Generate Content Bundle (Zip) ---"
# Payload for ContentGenerationRequest usually just empty or formats? 
# We need to make sure we pass whatever schema is required. 
# Looking at contracts.py or main.py: req: ContentGenerationRequest matches "output_formats" probably.
curl -X POST "$HOST/courses/$COURSE_ID/content/generate" \
  -H "Content-Type: application/json" \
  -d '{"output_formats": ["zip"]}' > response.json

cat response.json

echo "--- 8. Verify Zip Exists ---"
ZIP_PATH=$(grep -o '"artifact_url": *"[^"]*"' response.json | cut -d'"' -f4)
echo "Zip Path: $ZIP_PATH"

if [ -f "$ZIP_PATH" ]; then
    echo "✅ Zip file created successfully."
    
    # Optional: Unzip and inspect manifest
    mkdir -p verify_unzip
    unzip -o "$ZIP_PATH" -d verify_unzip
    if [ -f "verify_unzip/manifest.json" ]; then
        echo "✅ Manifest found."
        cat verify_unzip/manifest.json
    else
        echo "❌ Manifest MISSING."
        exit 1
    fi
else
    echo "❌ Zip file NOT found."
    exit 1
fi

echo "✅ Content Bundle Verification Complete"

kill $SERVER_PID
