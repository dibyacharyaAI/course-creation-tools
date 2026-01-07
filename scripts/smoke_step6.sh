#!/bin/bash
set -e

API_URL="http://localhost:3000/api/lifecycle"
# Randomize Course Code to avoid conflict
RAND_HASH=$(date +%s)
COURSE_DATA="{\"title\":\"SMOKE_TEST_STEP6_$RAND_HASH\", \"course_code\":\"SMOKE_$RAND_HASH\", \"obe_metadata\":{\"modules\":[{\"id\":\"m1\",\"title\":\"Module 1\",\"topics\":[{\"id\":\"t1\",\"title\":\"Topic 1\"}]}]}}"

echo "========================================"
echo "    BOSS KG MVP - SMOKE TEST (Step 6)"
echo "========================================"

# 1. Create Course
echo "[1] Creating Course..."
CREATE_RESP=$(curl -s -X POST "$API_URL/courses" \
  -H "Content-Type: application/json" \
  -d "$COURSE_DATA")
COURSE_ID=$(echo "$CREATE_RESP" | jq -r '.id')
echo "    -> Course ID: $COURSE_ID"

# 2. Build Graph (Populates graph from blueprint)
echo "[2] Building Graph..."
# Initial build should take blueprint and create graph nodes
curl -s -X POST "$API_URL/courses/$COURSE_ID/graph/build" > /dev/null
echo "    -> Initial Graph Built."

# 3. Generate Topic (Simulated with Auto-Sync)
# Fetch Course to get blueprint/graph
COURSE_RESP=$(curl -s "$API_URL/courses/$COURSE_ID")
# Extract Topic ID from Blueprint
TOPIC_ID=$(echo "$COURSE_RESP" | jq -r '.blueprint.modules[0].topics[0].id')
echo "    -> Generating for Topic ID: $TOPIC_ID"

GEN_RESP=$(curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate?auto_sync=true")
echo "    -> Generation Triggered. Response: $GEN_RESP"

# Wait for job completion (Simulated by sleep + check graph)
echo "    -> Waiting for Auto-Sync..."
sleep 5

# 4. Get Graph & Verify Slides
echo "[4] Verifying Graph (SoT)..."
GRAPH_RESP=$(curl -s "$API_URL/courses/$COURSE_ID/graph")
SLIDE_COUNT=$(echo "$GRAPH_RESP" | grep -c "bullets")

if [ "$SLIDE_COUNT" -gt 0 ]; then
    echo "    ✅ Graph contains slides (Auto-Sync Worked!)"
else
    echo "    ❌ Graph Missing Slides. Dump: ${GRAPH_RESP:0:200}..."
    exit 1
fi

# 5. Patch Slide (Edit)
# Find a slide ID
SLIDE_ID=$(echo "$GRAPH_RESP" | jq -r '.children[0].children[0].children[0].children[0].id')
if [ "$SLIDE_ID" == "null" ]; then
    # Try different path if structure varies
     SLIDE_ID=$(echo "$GRAPH_RESP" | jq -r '.children[0].children[0].children[0].id')
fi
echo "    -> Patching Slide ID: $SLIDE_ID"

PATCH_RESP=$(curl -s -X PATCH "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/slides/$SLIDE_ID" \
  -H "Content-Type: application/json" \
  -d '{"title": "EDTITED BY SMOKE TEST"}')

# Verify Edit
if [[ "$PATCH_RESP" == *"EDTITED BY SMOKE TEST"* ]]; then
    echo "    ✅ Slide Edit Persisted in Graph."
else
    echo "    ❌ Slide Edit Failed."
    exit 1
fi

# 6. Approve Topic
echo "[6] Approving Topic..."
curl -s -X POST "$API_URL/courses/$COURSE_ID/topics/$TOPIC_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"status":"APPROVED", "comment":"Smoke Test Passed"}' > /dev/null
echo "    -> Topic Approved."

# 7. Export (Force=True)
echo "[7] Exporting PPT (Force=True)..."
EXPORT_RESP=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses/$COURSE_ID/export/ppt?force=true")

if [ "$EXPORT_RESP" -eq 200 ]; then
    echo "    ✅ Export (Force=True) Succeeded."
else
    echo "    ❌ Export Failed with status $EXPORT_RESP"
    exit 1
fi

# 7b. Export (Force=False) - Should also pass because we APPROVED it
echo "[7b] Exporting PPT (Force=False - After Approval)..."
EXPORT_STRICT_RESP=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/courses/$COURSE_ID/export/ppt?force=false")

if [ "$EXPORT_STRICT_RESP" -eq 200 ]; then
    echo "    ✅ Export (Strict) Succeeded (Topic Approved)."
else
    echo "    ❌ Export (Strict) Failed despite Approval! Status: $EXPORT_STRICT_RESP"
    exit 1
fi

echo "========================================"
echo "    SMOKE TEST PASSED 🚀"
echo "========================================"
