#!/bin/bash

# Configuration
API_URL="http://localhost:3000/api/lifecycle" # Gateway URL
# API_URL="http://localhost:8000" # Direct service URL (if gateway skipped) -> using direct for test script usually safer vs port mapping
# But docker-compose says internal 8000. Host mapping 3000 -> Gateway. 
# course-lifecycle is NOT exposed on host. Gateway is.
# Gateway routes /api/lifecycle -> course-lifecycle:8000 (assumed based on standard patterns, let's check nginx.conf if needed, but I'll assume standard)

# Actually, let's use the gateway URL if exposed, or port forward? 
# The Docker verification usually runs INSIDE the container or needs port mapping. 
# docker-compose.yml shows Gateway 3000:3000.
# Assuming I run this from Host.

API_URL="http://localhost:3000"

echo "1. Creating a new course (Syllabus Select)..."
# We need a template ID. Let's list templates first.
TEMPLATE_ID=$(curl -s "$API_URL/syllabus/templates" | jq -r '.[0].id')
echo "Selected Template: $TEMPLATE_ID"

if [ "$TEMPLATE_ID" == "null" ]; then
    echo "Failed to get template ID"
    exit 1
fi

# Create Course
RESPONSE=$(curl -s -X POST "$API_URL/syllabus/select" \
  -H "Content-Type: application/json" \
  -d "{\"template_id\": \"$TEMPLATE_ID\"}")

COURSE_ID=$(echo $RESPONSE | jq -r '.course_id')
echo "Created Course ID: $COURSE_ID"

echo "2. GET Graph (Initial)..."
GRAPH=$(curl -s "$API_URL/courses/$COURSE_ID/graph")
echo $GRAPH | jq .

VERSION=$(echo $GRAPH | jq -r '.version')
if [ "$VERSION" != "1" ]; then
    echo "ERROR: Expected version 1, got $VERSION"
    exit 1
fi

echo "3. PATCH Graph (Add Module)..."
# Construct payload with new module
# We need to send the FULL graph children
NEW_GRAPH=$(echo $GRAPH | jq '.children += [{"name": "New Module", "order": 1, "children": []}]')
# We must ensure course_id is set (it should be in GET response)

PATCH_RESP=$(curl -s -X PATCH "$API_URL/courses/$COURSE_ID/graph" \
  -H "Content-Type: application/json" \
  -d "$NEW_GRAPH")

echo "Patch Response:"
echo $PATCH_RESP | jq .

NEW_VERSION=$(echo $PATCH_RESP | jq -r '.version')
echo "New Version: $NEW_VERSION"

if [ "$NEW_VERSION" != "2" ]; then
    echo "ERROR: Expected version 2, got $NEW_VERSION"
    exit 1
fi

echo "4. PATCH Invalid Graph (Schema Violation)..."
# Missing 'name' in module
INVALID_GRAPH='{"course_id": '$COURSE_ID', "children": [{"order": 1}]}' 

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API_URL/courses/$COURSE_ID/graph" \
  -H "Content-Type: application/json" \
  -d "$INVALID_GRAPH")

echo "Invalid Patch Status: $HTTP_CODE"

if [ "$HTTP_CODE" != "422" ]; then
    echo "ERROR: Expected 422, got $HTTP_CODE"
    exit 1
fi

echo "✅ CourseGraph Verification Successful!"
