#!/bin/bash
set -x
set -e

HOST="http://localhost:8000"

echo "--- 1. Creating Course ---"
COURSE_PAYLOAD='{
  "title": "Topic Flow Demo",
  "program_name": "B.Tech",
  "course_code": "TOPIC101"
}'
echo "Creating Course..."
curl -v -X POST "$HOST/courses" \
  -H "Content-Type: application/json" \
  -d "$COURSE_PAYLOAD"

# Assume ID 1 for SQLite fresh DB
COURSE_ID=1

echo "Using Course ID: $COURSE_ID"

TOPIC_ID="T_DEMO_1"
echo "--- 3. Trigger Generation for $TOPIC_ID ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate" \
  -H "Content-Type: application/json" -d '{}'

echo "--- 4. Verify Status (Should be GENERATED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID"

echo "--- 5. Run Verification (Check constraints) ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/verify" \
  -H "Content-Type: application/json" -d '{}'

echo "--- 6. Verify Status (Should be VERIFIED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID"

echo "--- 7. Approve Topic ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/approve" \
  -H "Content-Type: application/json" \
  -d '{ "notes": "Looks good to me", "reviewer": "Antigravity" }'

echo "--- 8. Final Status Check (Should be APPROVED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID"

echo "✅ Topic Flow Demo Complete"
