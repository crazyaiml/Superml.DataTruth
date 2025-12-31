#!/bin/bash

# DataTruth - Stop Script
# This script stops all DataTruth services

echo "🛑 Stopping DataTruth..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop Frontend UI (if running)
echo -e "${BLUE}🎨 Stopping Frontend UI...${NC}"
pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✓ Frontend UI stopped${NC}" || echo -e "${YELLOW}⚠️  Frontend UI not running${NC}"

# Stop API server (if running in background)
echo -e "${BLUE}📦 Stopping API server...${NC}"
pkill -f "uvicorn src.api.main:app" 2>/dev/null && echo -e "${GREEN}✓ API server stopped${NC}" || echo -e "${YELLOW}⚠️  API server not running${NC}"

# Check if Docker services were started by start.sh
echo ""
echo -e "${BLUE}📦 Checking Docker services...${NC}"

# Check if postgres container is running
if docker ps --filter "name=postgres" --filter "status=running" -q | grep -q .; then
    echo -e "${YELLOW}Stopping PostgreSQL container...${NC}"
    docker-compose stop postgres
    echo -e "${GREEN}✓ PostgreSQL stopped${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL container not running${NC}"
fi

# Check if redis container is running
if docker ps --filter "name=redis" --filter "status=running" -q | grep -q .; then
    echo -e "${YELLOW}Stopping Redis container...${NC}"
    docker-compose stop redis
    echo -e "${GREEN}✓ Redis stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Redis container not running${NC}"
fi

echo ""
echo -e "${GREEN}✓ DataTruth stopped${NC}"
echo ""
echo "To start again, run: ./start.sh"
echo ""
echo -e "${YELLOW}Note: To completely remove containers, run: docker-compose down${NC}"
