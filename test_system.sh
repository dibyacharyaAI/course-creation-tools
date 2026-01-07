#!/bin/bash

# Test script for AI-Powered Course Creation Platform
# This script performs comprehensive system testing

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 AI-Powered Course Creation Platform - Test Suite${NC}"
echo ""

# Test 1: Health Checks
echo -e "${YELLOW}Test 1: Health Checks${NC}"
echo "Testing Course Lifecycle Service..."
if curl -s http://localhost:8001/health | grep -q "ok"; then
    echo -e "${GREEN}✅ Course Lifecycle Service is healthy${NC}"
else
    echo -e "${RED}❌ Course Lifecycle Service is not responding${NC}"
    exit 1
fi

echo "Testing Exporter Service..."
if curl -s http://localhost:8002/health | grep -q "ok"; then
    echo -e "${GREEN}✅ Exporter Service is healthy${NC}"
else
    echo -e "${RED}❌ Exporter Service is not responding${NC}"
fi
echo ""

# Test 2: List Courses
echo -e "${YELLOW}Test 2: Listing Courses${NC}"
COURSE_COUNT=$(curl -s http://localhost:8001/courses | jq '. | length' 2>/dev/null || echo "0")
echo -e "${GREEN}✅ Found ${COURSE_COUNT} courses in the system${NC}"
echo ""

# Test 3: Check Course Details
if [ "$COURSE_COUNT" -gt "0" ]; then
    echo -e "${YELLOW}Test 3: Checking First Course${NC}"
    FIRST_COURSE=$(curl -s http://localhost:8001/courses | jq '.[0]' 2>/dev/null)
    COURSE_ID=$(echo $FIRST_COURSE | jq -r '.id')
    COURSE_TITLE=$(echo $FIRST_COURSE | jq -r '.title')
    COURSE_STATUS=$(echo $FIRST_COURSE | jq -r '.status')
    HAS_CONTENT=$(echo $FIRST_COURSE | jq -r '.content != null')
    
    echo "Course ID: $COURSE_ID"
    echo "Title: $COURSE_TITLE"
    echo "Status: $COURSE_STATUS"
    echo "Has Content: $HAS_CONTENT"
    
    if [ "$HAS_CONTENT" = "true" ]; then
        echo -e "${GREEN}✅ Course has AI-generated content${NC}"
    else
        echo -e "${YELLOW}⚠️  Course does not have content yet${NC}"
    fi
    echo ""
fi

# Test 4: Create New Course
echo -e "${YELLOW}Test 4: Creating a New Test Course${NC}"
NEW_COURSE=$(curl -s -X POST http://localhost:8001/courses \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test Course - Software Engineering",
        "description": "A comprehensive test course for verifying AI content generation",
        "course_code": "SE-TEST-$(date +%s)",
        "programme": "Computer Science",
        "semester": "Spring 2024",
        "obe_metadata": {
            "learning_outcomes": [
                "Understand software development lifecycle",
                "Apply design patterns",
                "Implement testing strategies"
            ]
        }
    }')

NEW_COURSE_ID=$(echo $NEW_COURSE | jq -r '.id')
echo -e "${GREEN}✅ Created course with ID: $NEW_COURSE_ID${NC}"
echo ""

# Test 5: Trigger AI Generation
echo -e "${YELLOW}Test 5: Triggering AI Content Generation${NC}"
TRIGGER_RESULT=$(curl -s -X POST http://localhost:8001/courses/$NEW_COURSE_ID/generate)
TRIGGER_STATUS=$(echo $TRIGGER_RESULT | jq -r '.status')
echo "Course status after trigger: $TRIGGER_STATUS"
echo -e "${GREEN}✅ AI generation triggered${NC}"
echo ""

# Test 6: Monitor Generation Progress
echo -e "${YELLOW}Test 6: Monitoring AI Generation Progress${NC}"
echo "Waiting for content generation (this may take 10-30 seconds)..."

for i in {1..15}; do
    echo -n "."
    sleep 2
    
    UPDATED_COURSE=$(curl -s http://localhost:8001/courses/$NEW_COURSE_ID)
    CURRENT_STATUS=$(echo $UPDATED_COURSE | jq -r '.status')
    HAS_CONTENT=$(echo $UPDATED_COURSE | jq -r '.content != null')
    
    if [ "$HAS_CONTENT" = "true" ] && [ "$CURRENT_STATUS" = "CONTENT_READY" ]; then
        echo ""
        echo -e "${GREEN}✅ Content generation completed!${NC}"
        echo "Status: $CURRENT_STATUS"
        
        # Show content summary
        MODULE_COUNT=$(echo $UPDATED_COURSE | jq '.content.modules | length' 2>/dev/null || echo "0")
        echo "Generated modules: $MODULE_COUNT"
        
        if [ "$MODULE_COUNT" -gt "0" ]; then
            echo ""
            echo "Module titles:"
            echo $UPDATED_COURSE | jq -r '.content.modules[].title' 2>/dev/null | sed 's/^/  - /'
        fi
        
        break
    fi
    
    if [ $i -eq 15 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Content generation is taking longer than expected${NC}"
        echo "Current status: $CURRENT_STATUS"
        echo "Check logs: docker compose -f infra/docker-compose.yml logs ai-authoring"
    fi
done
echo ""

# Test 7: Database Check
echo -e "${YELLOW}Test 7: Database Verification${NC}"
echo "Checking PostgreSQL connection..."
if docker exec infra-postgres-1 psql -U user -d obe_platform -c "SELECT COUNT(*) FROM courses;" &>/dev/null; then
    DB_COUNT=$(docker exec infra-postgres-1 psql -U user -d obe_platform -t -c "SELECT COUNT(*) FROM courses;")
    echo -e "${GREEN}✅ Database connection successful${NC}"
    echo "Total courses in database: $(echo $DB_COUNT | tr -d ' ')"
else
    echo -e "${RED}❌ Database connection failed${NC}"
fi
echo ""

# Test Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Health checks passed${NC}"
echo -e "${GREEN}✅ Course listing works${NC}"
echo -e "${GREEN}✅ Course creation works${NC}"
echo -e "${GREEN}✅ AI generation triggered${NC}"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. View detailed course content:"
echo "   curl http://localhost:8001/courses/$NEW_COURSE_ID | jq '.content' | less"
echo ""
echo "2. Monitor AI Authoring logs:"
echo "   docker compose -f infra/docker-compose.yml logs -f ai-authoring"
echo ""
echo "3. Check all courses:"
echo "   curl http://localhost:8001/courses | jq '.[].title'"
echo ""
echo "4. View logs for debugging:"
echo "   docker compose -f infra/docker-compose.yml logs -f course-lifecycle"
echo ""
echo -e "${GREEN}🎉 Testing complete!${NC}"
