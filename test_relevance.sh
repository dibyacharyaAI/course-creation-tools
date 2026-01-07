#!/bin/bash

# Configuration
API_URL="http://localhost:8001"
COURSE_LIFECYCLE_URL="http://localhost:8001"

echo "Starting Relevance Test..."

# Function to create and generate course
test_course() {
    local title="$1"
    local description="$2"
    local expected_result="$3" # "success" or "failure"

    echo "---------------------------------------------------"
    echo "Testing Topic: $title"
    
    # Create Course
    local course_code="TEST-$(date +%s)"
    echo "Creating course..."
    response=$(curl -s -X POST "$COURSE_LIFECYCLE_URL/courses" \
        -H "Content-Type: application/json" \
        -d "{
            \"title\": \"$title\",
            \"course_code\": \"$course_code\",
            \"description\": \"$description\",
            \"programme\": \"B.Tech\",
            \"semester\": \"6\",
            \"credits\": 3,
            \"obe_metadata\": {}
        }")

    course_id=$(echo $response | jq -r '.id')
    
    if [ "$course_id" == "null" ]; then
        echo "Failed to create course. Response: $response"
        return 1
    fi
    
    echo "Course created with ID: $course_id"

    # Trigger Generation
    echo "Triggering generation..."
    gen_response=$(curl -s -X POST "$COURSE_LIFECYCLE_URL/courses/$course_id/generate" \
        -H "Content-Type: application/json")
    
    echo "Generation triggered. Waiting for processing..."
    
    # Poll for status
    for i in {1..12}; do
        sleep 5
        status_response=$(curl -s -X GET "$COURSE_LIFECYCLE_URL/courses/$course_id")
        status=$(echo $status_response | jq -r '.status')
        echo "Poll $i: Status is $status"
        
        if [ "$status" == "CONTENT_GENERATED" ] || [ "$status" == "FAILED" ] || [ "$status" == "CONTENT_READY" ]; then
            break
        fi
    done

    if [ "$expected_result" == "success" ]; then
        if [ "$status" == "CONTENT_GENERATED" ] || [ "$status" == "GENERATING_CONTENT" ] || [ "$status" == "CONTENT_READY" ]; then
             echo "✅ Success: Relevant topic accepted."
        else
             echo "❌ Failure: Relevant topic rejected or failed. Status: $status"
             # Check logs if possible, or print response
        fi
    else
        if [ "$status" == "FAILED" ] || [ "$status" == "DRAFT" ]; then
             echo "✅ Success: Irrelevant topic rejected (or failed as expected)."
        else
             echo "❌ Failure: Irrelevant topic accepted? Status: $status"
        fi
    fi
}

# Test Case 1: Relevant Topic
test_course "Water Supply Engineering" "Basics of water treatment and supply systems." "success"

# Test Case 2: Irrelevant Topic
test_course "Ancient Roman History" "History of the Roman Empire." "failure"

echo "---------------------------------------------------"
echo "Test Complete."
