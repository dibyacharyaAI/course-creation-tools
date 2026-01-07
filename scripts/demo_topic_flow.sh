#!/bin/bash
set -e

HOST="http://localhost:8000"
COURSE_ID=999

echo "--- 1. Creating Course ---"
# We assume course 999 might exist or we just use it implicitly if DB seeding allows or we assume we can post to it.
# Actually, let's create a fresh course to be safe, or just reuse 1 if we know it exists. 
# Let's try to create one first to get a valid ID.
COURSE_PAYLOAD='{
  "title": "Topic Flow Demo",
  "program_name": "B.Tech",
  "course_code": "TOPIC101"
}'
echo "Creating Course..."
curl -X POST "$HOST/courses" \
  -H "Content-Type: application/json" \
  -d "$COURSE_PAYLOAD"

# Simplified creation assuming endpoint exists or we skip if we can't parse ID easily without jq
# For now, let's assume we use ID 1 which usually exists in dev/demo
COURSE_ID=1


echo "Using Course ID: $COURSE_ID"

echo "--- 2. Setting Canonical Data (Optional but good practice) ---"
# We skip this for brevity as we just want to test TopicJob specific endpoints

TOPIC_ID="T_DEMO_1"

echo "--- 3. Trigger Generation for $TOPIC_ID ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/generate" \
  -H "Content-Type: application/json" -d '{}'

echo -e "\n\n--- 4. Verify Status (Should be GENERATED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID"

echo -e "\n\n--- 5. Run Verification (Check constraints) ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/verify" \
  -H "Content-Type: application/json" -d '{}'

echo -e "\n\n--- 6. Verify Status (Should be VERIFIED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID" | grep "VERIFIED"

echo -e "\n\n--- 7. Approve Topic ---"
curl -X POST "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID/ppt/approve" \
  -H "Content-Type: application/json" \
  -d '{ "notes": "Looks good to me", "reviewer": "Antigravity" }'

echo -e "\n\n--- 8. Final Status Check (Should be APPROVED) ---"
curl -s "$HOST/courses/$COURSE_ID/topics/$TOPIC_ID" | grep "APPROVED"

echo -e "\n\n✅ Topic Flow Demo Complete"
