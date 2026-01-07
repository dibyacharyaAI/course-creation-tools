#!/bin/bash
set -e
# Adjust course ID as needed
COURSE_ID=9
# Generate slides to obtain a trace_id
RESPONSE=$(curl -s -X POST http://localhost:3000/ppt/slides/generate -H "Content-Type: application/json" -d "{\"course_id\":$COURSE_ID,\"deck_mode\":\"QUICK_DECK\"}")
TRACE=$(echo "$RESPONSE" | grep -o '"trace_id":"[^"]*' | cut -d'"' -f4)
if [ -z "$TRACE" ]; then
  echo "Failed to obtain trace_id"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Obtained trace_id: $TRACE"
# Render PPTX
curl -s -X POST http://localhost:3000/api/lifecycle/ppt/render -H "Content-Type: application/json" -d "{\"course_id\":$COURSE_ID,\"trace_id\":\"$TRACE\"}" -o /dev/null

echo "PPT render succeeded"
# Approve PPT
curl -s -X POST http://localhost:3000/api/lifecycle/ppt/approve -H "Content-Type: application/json" -d "{\"course_id\":$COURSE_ID,\"trace_id\":\"$TRACE\",\"approved\":true}" -o /dev/null

echo "PPT approval succeeded"
exit 0
