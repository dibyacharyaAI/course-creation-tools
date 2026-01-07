#!/bin/bash
set -x
set -e

HOST="http://localhost:8000"

echo "--- 1. Resetting DB ---"
rm test.db || true

echo "--- 2. Starting Server (Background) ---"
# We need to make sure we kill it later
# Assuming python3 available
DATABASE_URL=sqlite:///./test.db PYTHONPATH=. uvicorn services.course-lifecycle.app.main:app --host 0.0.0.0 --port 8000 > server_edit.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 15 # Wait for startup

echo "--- 3. Creating Course ---"
COURSE_PAYLOAD='{
  "title": "Slide Edit Demo",
  "program_name": "B.Tech",
  "course_code": "EDIT101"
}'
curl -X POST "$HOST/courses" \
  -H "Content-Type: application/json" \
  -d "$COURSE_PAYLOAD"

COURSE_ID=1
TOPIC_ID="T_EDIT_1"

echo "--- 4. Trigger Generation (Version 1) ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate" \
  -H "Content-Type: application/json" -d '{}'

echo "--- 5. Get Current Version (Should be 1) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID"

echo "--- 6. PATCH Slides (Edit Title -> Version 2) ---"
# Payload must obey SlideStructure: { "slides": [ {id, title, bullets, ...} ] }
# We need 8 slides for verification to pass
SLIDES_PAYLOAD='{
  "slides": [
    {"id": "s1", "title": "Edited Slide 1", "bullets": ["b1"], "tags": {}},
    {"id": "s2", "title": "Slide 2", "bullets": ["b1"], "tags": {}},
    {"id": "s3", "title": "Slide 3", "bullets": ["b1"], "tags": {}},
    {"id": "s4", "title": "Slide 4", "bullets": ["b1"], "tags": {}},
    {"id": "s5", "title": "Slide 5", "bullets": ["b1"], "tags": {}},
    {"id": "s6", "title": "Slide 6", "bullets": ["b1"], "tags": {}},
    {"id": "s7", "title": "Slide 7", "bullets": ["b1"], "tags": {}},
    {"id": "s8", "title": "Slide 8", "bullets": ["b1"], "tags": {}}
  ]
}'

curl -X PATCH "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/slides" \
  -H "Content-Type: application/json" \
  -d "$SLIDES_PAYLOAD"

echo "--- 7. Verify Version (Should be 2 and VERIFIED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID" | grep '"version":2'
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID" | grep '"status":"VERIFIED"'

echo "✅ Slide Edit Verification Complete"

kill $SERVER_PID
