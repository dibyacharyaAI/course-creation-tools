#!/bin/bash
set -e

# Boss KG MVP Flow Verification
# Tests: Auto-Sync, Export Constraints, PPT Generation

API_URL="http://localhost:3000/api/lifecycle"
COURSE_ID=101
TOPIC_ID="introduction"

echo "============================================"
echo "BOSS FLOW VERIFICATION"
echo "============================================"

# 1. Create Course
echo "[1] Creating Course..."
COURSE_RESP=$(curl -s -X POST "$API_URL/courses" \
  -H "Content-Type: application/json" \
  -d '{"title": "Boss Flow Test", "course_code": "BOSS202", "obe_metadata": {"modules": [{"id": "m1", "title": "Module 1", "topics": [{"id": "introduction", "title": "Introduction"}]}]}}')
COURSE_ID=$(echo $COURSE_RESP | grep -o '"id":[0-9]*' | head -1 | awk -F: '{print $2}')
echo "    -> Created Course ID: $COURSE_ID"

# Build Initial Graph
echo "[2] Building Initial Graph..."
curl -s -X POST "$API_URL/courses/$COURSE_ID/graph/build" > /dev/null
echo "    -> Initial Graph Built."

# 2. Trigger Generation with Auto-Sync
echo "[3] Triggering Generation (Step 6) with Auto-Sync..."
# Note: auto_sync defaults to true in our code change
GEN_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate?auto_sync=true")
JOB_ID=$(echo $GEN_RESP | grep -o '"job_id":[0-9]*' | head -1 | awk -F: '{print $2}')
echo "    -> Triggered Job ID: $JOB_ID"

# Wait for Generation
echo "    -> Waiting for generation..."
for i in {1..45}; do
  JOB_RESP=$(curl -s "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID")
  STATUS=$(echo $JOB_RESP | grep -o '"status":"[^"]*"' | head -1 | awk -F: '{print $2}' | tr -d '"')
  if [ "$STATUS" == "GENERATED" ]; then
    echo "    -> Generated! (Status: $STATUS)"
    break
  fi
  sleep 2
done

# 3. Verify Graph contains data WITHOUT manual build (Auto-Sync Check)
echo "[4] Checking Graph for Auto-Synced Data..."
GRAPH_RESP=$(curl -s "$API_URL/courses/$COURSE_ID/graph")
# Check for bullets content which indicates slides
SLIDE_MATCH=$(echo "$GRAPH_RESP" | grep -c "bullets")
if [ "$SLIDE_MATCH" -gt 0 ]; then
    echo "    ✅ Graph contains slides (Auto-Sync Worked!)"
else
    echo "    ❌ Graph does NOT contain slides. Auto-Sync Failed."
    # Fail hard and show response
    echo "    -> Graph Dump: $GRAPH_RESP"
    exit 1
fi

# 4. Attempt Export WITHOUT Approval (Should Fail)
echo "[5] Testing Export Gate (Expect Failure)..."
EXPORT_FAIL=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses/$COURSE_ID/export/pdf?topic_id=$TOPIC_ID&force=false")
if [ "$EXPORT_FAIL" == "422" ]; then
    echo "    ✅ Export Blocked as expected (HTTP 422)"
else
    echo "    ❌ Export NOT Blocked (HTTP $EXPORT_FAIL)"
    exit 1
fi

# 5. Export with FORCE (Should Succeed)
echo "[6] Testing Export Bypass (force=true)..."
EXPORT_PASS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses/$COURSE_ID/export/pdf?topic_id=$TOPIC_ID&force=true")
if [ "$EXPORT_PASS" == "200" ]; then
    echo "    ✅ Export Bypass Succeeded (HTTP 200)"
else
    echo "    ❌ Export Bypass Failed (HTTP $EXPORT_PASS)"
    exit 1
fi

# 6. Approve Topic
echo "[7] Approving Topic..."
curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"status": "APPROVED"}' > /dev/null
echo "    -> Approved."

# 7. Export WITHOUT Force (Should Succeed now)
echo "[8] Testing Final Export (force=false)..."
EXPORT_FINAL=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses/$COURSE_ID/export/pdf?topic_id=$TOPIC_ID&force=false")
if [ "$EXPORT_FINAL" == "200" ]; then
    echo "    ✅ Final Export Succeeded (HTTP 200)"
else
    echo "    ❌ Final Export Failed (HTTP $EXPORT_FINAL)"
    exit 1
fi

echo "============================================"
echo "ALL CHECKS PASSED"
echo "============================================"
