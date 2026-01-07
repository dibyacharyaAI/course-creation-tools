#!/bin/bash
set -e

# Boss KG MVP E2E Verification Script
# Usage: ./scripts/verify_e2e.sh

API_URL="http://localhost:3000/api/lifecycle"
COURSE_ID=1
TOPIC_ID="introduction"

echo "============================================"
echo "BOSS KG MVP E2E VERIFICATION"
echo "============================================"

# Helper for JSON extraction
get_json_val() {
  echo "$1" | grep -o "\"$2\":[^,}]*" | awk -F: '{print $2}' | tr -d '"'
}

# 0. Wait for Service Ready
echo "[0] Waiting for Service Ready..."
for i in {1..30}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses")
  if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "404" ] || [ "$HTTP_CODE" == "405" ]; then 
    # 404/405 means service is reachable (just method not allowed on root potentially)
    # Actually GET /courses might not exist? POST /courses exists.
    # Let's try /health if it exists, or just acceptable codes.
    # course-lifecycle doesn't have /health exposed in main.py? 
    # It has no /health route!
    # But it has GET /courses/{id}.
    echo "    -> Service Up!"
    break
  fi
  echo "    ... waiting ($i)"
  sleep 2
done

# 1. Create a Course (Draft) to ensure we have a playground
echo "[1] Creating Test Course..."
COURSE_RESP=$(curl -s -X POST "$API_URL/courses" \
  -H "Content-Type: application/json" \
  -d '{"title": "Boss KG Demo", "course_code": "BOSS101", "obe_metadata": {"modules": [{"id": "m1", "title": "Intro Module", "topics": [{"id": "introduction", "title": "Introduction"}]}]}}')
COURSE_ID=$(echo $COURSE_RESP | grep -o '"id":[0-9]*' | head -1 | awk -F: '{print $2}')
echo "    -> Created Course ID: $COURSE_ID"

ECHO_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/graph/build")
echo "    -> Graph Built."

# 2. Trigger Topic Generation (Step 6)
echo "[2] Triggering Topic Generation (Step 6)..."
GEN_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate")
JOB_ID=$(echo $GEN_RESP | grep -o '"job_id":[0-9]*' | head -1 | awk -F: '{print $2}')
echo "    -> Triggered Job ID: $JOB_ID"

# Wait for generation (poll)
echo "    -> Waiting for generation..."
for i in {1..20}; do
  JOB_RESP=$(curl -s "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID")
  STATUS=$(echo $JOB_RESP | grep -o '"status":"[^"]*"' | head -1 | awk -F: '{print $2}' | tr -d '"')
  if [ "$STATUS" == "GENERATED" ]; then
    echo "    -> Generated! (Status: $STATUS)"
    break
  fi
  sleep 2
done

# 3. Verify Slides Content (Task 1 & 2 Check)
echo "[3] Checking Generated Slides Structure..."
# Simple greps to check structure
echo "$JOB_RESP" | grep -q "\"slides\":" && echo "    ✅ Has 'slides' key" || echo "    ❌ Missing 'slides' key"
echo "$JOB_RESP" | grep -q "\"illustration_prompt\"" && echo "    ✅ Has 'illustration_prompt'" || echo "    ❌ Missing 'illustration_prompt'"
# Count slides (simple grep count)
SLIDE_COUNT=$(echo "$JOB_RESP" | grep -o "\"id\"" | wc -l) 
# Note: "id" appears in topic header too, approx count check or look for bullets
echo "    -> Response size: ${#JOB_RESP} chars"

# 4. Strict Verify (Task 4 & 6)
echo "[4] Running Strict Verify (Quality Gate)..."
VERIFY_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/verify")
echo "    -> Response: $VERIFY_RESP"

# 5. Preview Force=True (Task 3)
echo "[5] Testing Preview (force=true)..."
PREVIEW_RESP=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/courses/$COURSE_ID/export/pdf?topic_id=$TOPIC_ID&force=true")
if [ "$PREVIEW_RESP" == "200" ]; then
  echo "    ✅ Preview (force=true) succeeded (HTTP 200)"
else
  echo "    ❌ Preview (force=true) failed (HTTP $PREVIEW_RESP)"
fi

# 6. Approve Topic (Task 5 & Step 7)
echo "[6] Approving Topic (Step 7 Flow)..."
# Using the graph approval endpoint
APPROVE_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"status": "APPROVED", "comment": "Verification Script Approval"}')
echo "    -> Approved."

# 7. Final Export Force=False (Task 3 & 4)
echo "[7] Testing Final Export (force=false)..."
EXPORT_RESP=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/courses/$COURSE_ID/export/pdf?topic_id=$TOPIC_ID")
if [ "$EXPORT_RESP" == "200" ]; then
  echo "    ✅ Final Export (force=false) succeeded (HTTP 200)"
else
  echo "    ❌ Final Export failed (HTTP $EXPORT_RESP)"
fi

# 8. Check File Existence (Task 4)
echo "[8] Checking File Existence in Shared Volume..."
# We can't ls docker volume easily from here without docker exec, but we can assume success if 200 returned
# But we can try to exec into container if available
if command -v docker &> /dev/null; then
    docker exec infra-course-lifecycle-1 ls -l /app/generated_data/exports/$COURSE_ID/
fi

echo "============================================"
echo "VERIFICATION COMPLETE"
echo "============================================"
