#!/bin/bash

# DataTruth - Start Script
# This script starts all necessary services for DataTruth

set -e

echo "🚀 Starting DataTruth..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install -e ".[dev]"
    echo ""
else
    source .venv/bin/activate
fi

# Check if PostgreSQL is already running
echo -e "${BLUE}📦 Checking services...${NC}"
POSTGRES_RUNNING=false

# Check if postgres is running on port 5432
if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL already running on port 5432${NC}"
    POSTGRES_RUNNING=true
else
    echo "Starting PostgreSQL in Docker..."
    docker-compose up -d postgres
    sleep 3
    
    # Check PostgreSQL
    echo -n "Checking PostgreSQL... "
    if docker-compose exec -T postgres pg_isready -U datatruth_admin > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        POSTGRES_RUNNING=true
    else
        echo -e "${RED}✗${NC}"
        echo "PostgreSQL failed to start. Check logs with: docker-compose logs postgres"
        exit 1
    fi
fi

# Start Redis
REDIS_RUNNING=false

# Check if redis is running on port 6379
if lsof -Pi :6379 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis already running on port 6379${NC}"
    REDIS_RUNNING=true
else
    echo "Starting Redis in Docker..."
    docker-compose up -d redis
    sleep 2
fi

# Check Redis
if [ "$REDIS_RUNNING" = false ]; then
    echo -n "Checking Redis... "
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        REDIS_RUNNING=true
    else
        echo -e "${RED}✗${NC}"
        echo "Redis failed to start. Check logs with: docker-compose logs redis"
        exit 1
    fi
fi

echo ""

# Check if database is initialized
echo -e "${BLUE}📊 Checking database connection...${NC}"

# Load .env file to get database credentials
if [ -f .env ]; then
    export $(grep -v '^#' .env | sed 's/#.*//' | sed '/^$/d' | xargs)
fi

# Set defaults if not in .env
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-datatruth}
POSTGRES_USER=${POSTGRES_USER:-datatruth_admin}

# Test database connection
echo -n "Testing connection to ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}... "
if PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    
    # Check table count
    TABLE_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    
    if [ "$TABLE_COUNT" -gt "0" ]; then
        echo -e "${GREEN}✓ Database ready (${TABLE_COUNT} tables)${NC}"
    else
        echo -e "${YELLOW}⚠️  Database has no tables. You may need to run migrations.${NC}"
    fi
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Failed to connect to database at ${POSTGRES_HOST}:${POSTGRES_PORT}${NC}"
    echo "Please check your .env file and ensure PostgreSQL is running."
    exit 1
fi

echo ""

# Check if frontend dependencies are installed
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend dependencies not installed${NC}"
    if [ -d "frontend" ]; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    fi
fi

echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Start FastAPI application in background
echo -e "${BLUE}🌐 Starting DataTruth API...${NC}"
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓ API server started (PID: ${API_PID})${NC}"
echo -e "${GREEN}  Log file: logs/api.log${NC}"

# Wait for API to be ready
echo -n "Waiting for API to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

echo ""

# Start Frontend application
if [ -d "frontend" ]; then
    echo -e "${BLUE}🎨 Starting DataTruth UI...${NC}"
    cd frontend
    nohup npm run dev > ../logs/ui.log 2>&1 &
    UI_PID=$!
    echo -e "${GREEN}✓ UI server started (PID: ${UI_PID})${NC}"
    echo -e "${GREEN}  Log file: logs/ui.log${NC}"
    cd ..
    
    # Wait for UI to be ready (check logs instead of curl)
    echo -n "Waiting for UI to be ready..."
    for i in {1..20}; do
        if grep -q "Local:.*http" logs/ui.log 2>/dev/null; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        if [ $i -eq 20 ]; then
            echo -e " ${YELLOW}⚠${NC}"
            echo -e "${YELLOW}  UI is starting... check logs/ui.log for details${NC}"
        fi
        sleep 1
        echo -n "."
    done
fi

echo ""
echo -e "${GREEN}✅ DataTruth is running!${NC}"
echo ""
echo "Access the application:"
echo -e "  ${GREEN}🎨 UI:  http://localhost:3000${NC}"
echo -e "  ${GREEN}🌐 API: http://localhost:8000${NC}"
echo ""
echo "API Documentation:"
echo -e "  ${GREEN}http://localhost:8000/docs${NC} (Swagger UI)"
echo -e "  ${GREEN}http://localhost:8000/redoc${NC} (ReDoc)"
echo ""
echo "Log files:"
echo -e "  ${GREEN}API: logs/api.log${NC}"
echo -e "  ${GREEN}UI:  logs/ui.log${NC}"
echo ""
echo "View logs:"
echo -e "  ${YELLOW}tail -f logs/api.log${NC} (API logs)"
echo -e "  ${YELLOW}tail -f logs/ui.log${NC} (UI logs)"
echo ""
echo "To stop all services, run: ${YELLOW}./stop.sh${NC}"
echo ""
