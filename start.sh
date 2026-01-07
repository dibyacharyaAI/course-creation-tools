#!/bin/bash

# Startup script for AI-Powered Course Creation Platform
# This script helps start the entire system with proper Docker paths

set -e

echo "🚀 Starting AI-Powered Course Creation Platform..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Add Docker Desktop bin to PATH to ensure credential helpers are found
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

# Function to find Docker
find_docker() {
    # Try standard path first
    if command -v docker &> /dev/null; then
        echo "docker"
        return 0
    fi
    
    # Try Docker Desktop path
    if [ -f "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
        echo "/Applications/Docker.app/Contents/Resources/bin/docker"
        return 0
    fi
    
    # Try common symlink
    if [ -f "/usr/local/bin/docker" ]; then
        echo "/usr/local/bin/docker"
        return 0
    fi
    
    return 1
}

# Find Docker
DOCKER_CMD=$(find_docker)
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker not found!${NC}"
    echo ""
    echo "Please ensure Docker Desktop is installed and running:"
    echo "1. Open Docker Desktop app from Applications"
    echo "2. Wait for Docker to start (whale 🐳 icon in menu bar)"
    echo "3. Or add Docker to PATH: export PATH=\"/Applications/Docker.app/Contents/Resources/bin:\$PATH\""
    exit 1
fi

echo -e "${GREEN}✅ Found Docker at: $DOCKER_CMD${NC}"

# Check if Docker is running
if ! $DOCKER_CMD info &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker is not running${NC}"
    echo ""
    echo "Please start Docker Desktop:"
    echo "1. Open /Applications/Docker.app"
    echo "2. Wait for the whale icon in your menu bar"
    echo "3. Run this script again"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check for docker compose
if $DOCKER_CMD compose version &> /dev/null; then
    COMPOSE_CMD="$DOCKER_CMD compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}❌ Docker Compose not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose available${NC}"
echo ""

# Change to infra directory
cd "$(dirname "$0")/infra"

# Check for .env file
if [ ! -f "../.env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    if [ -f "../.env.example" ]; then
        cp ../.env.example ../.env
        echo -e "${GREEN}✅ Created .env file${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
fi

# Ask user for startup mode
echo "Select startup mode:"
echo "1) Start with logs (foreground)"
echo "2) Start in background (detached)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}🚀 Starting services in foreground...${NC}"
        echo "Press Ctrl+C to stop all services"
        echo ""
        $COMPOSE_CMD up --build
        ;;
    2)
        echo ""
        echo -e "${GREEN}🚀 Starting services in background...${NC}"
        $COMPOSE_CMD up --build -d
        
        echo ""
        echo -e "${GREEN}✅ Services started successfully!${NC}"
        echo ""
        echo "Service URLs:"
        echo "  • Access URL:       http://localhost:3000"
        echo "  • Lifecycle API:    http://localhost:3000/api/lifecycle"
        echo "  • Authoring API:    http://localhost:3000/api/authoring"
        echo ""
        echo "Useful commands:"
        echo "  • View status:  $COMPOSE_CMD ps"
        echo "  • View logs:    $COMPOSE_CMD logs -f"
        echo "  • Stop all:     $COMPOSE_CMD down"
        echo ""
        echo "📖 See testing_guide.md for complete testing instructions"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
