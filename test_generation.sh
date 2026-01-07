#!/bin/bash
set -e
BASE_URL="http://localhost:3000/api/lifecycle"

# 1. Restart Service
echo "Restarting Course Lifecycle Service..."
docker restart infra-course-lifecycle-1
echo "Waiting for service to be healthy..."
sleep 5

# 2. Get Course ID (Assume 9)
CID=9
echo "Using Course ID: $CID"

# 3. Generate Slides (Actual LLM Call)
echo "Generating Slides (QUICK_DECK)... This may take 20-30s..."
curl -s -X POST "$BASE_URL/ppt/slides/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"course_id\": $CID,
    \"deck_mode\": \"QUICK_DECK\"
  }" > result_gen.json

# 4. JSON Check
echo "Result:"
cat result_gen.json | head -n 20

TRACE_ID=$(cat result_gen.json | grep -o '"trace_id":"[^"]*"' | cut -d'"' -f4)
STATUS=$(cat result_gen.json | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

echo "Trace ID: $TRACE_ID"
echo "Status: $STATUS"

if [ "$STATUS" == "DRAFT_READY" ]; then
    echo "SUCCESS: Slides generated."
else
    echo "FAILURE: Validation check result_gen.json"
    exit 1
fi
