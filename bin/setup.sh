#!/bin/bash
#==============================================================================
# DataTruth Setup Script
# 
# Initializes DataTruth for first-time deployment
# Run this script after configuring .env file
#==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}             DataTruth - Production Setup Script${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

#==============================================================================
# Step 1: Check Prerequisites
#==============================================================================
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo "Please copy .env.production to .env and configure it:"
    echo "  cp .env.production .env"
    echo "  vi .env  # Update passwords, API keys, etc."
    exit 1
fi
echo -e "${GREEN}✓ .env file found${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not installed${NC}"
    echo "Please install Python 3.11+: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION installed${NC}"

echo ""

#==============================================================================
# Step 2: Load Environment Variables
#==============================================================================
echo -e "${YELLOW}[2/7] Loading environment configuration...${NC}"

# Source .env file
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo -e "${GREEN}✓ Environment: $ENVIRONMENT${NC}"
echo -e "${GREEN}✓ Internal DB: $INTERNAL_DB_NAME${NC}"
echo ""

#==============================================================================
# Step 3: Create Required Directories
#==============================================================================
echo -e "${YELLOW}[3/7] Creating required directories...${NC}"

mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "${PROJECT_ROOT}/data/uploads"
mkdir -p "${PROJECT_ROOT}/data/chroma"
mkdir -p "${PROJECT_ROOT}/data/backups"

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

#==============================================================================
# Step 4: Start Docker Services
#==============================================================================
echo -e "${YELLOW}[4/7] Starting Docker services...${NC}"

cd "$PROJECT_ROOT"
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

MAX_RETRIES=30
RETRY_COUNT=0
until docker-compose exec -T postgres pg_isready -U $INTERNAL_DB_ADMIN_USER -d postgres > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}✗ PostgreSQL failed to start after ${MAX_RETRIES} attempts${NC}"
        exit 1
    fi
    echo "Waiting for PostgreSQL... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
echo ""

#==============================================================================
# Step 5: Initialize Database
#==============================================================================
echo -e "${YELLOW}[5/7] Initializing database schema...${NC}"

# Create database if it doesn't exist
docker-compose exec -T postgres psql -U $INTERNAL_DB_ADMIN_USER -d postgres <<-EOSQL
    SELECT 'CREATE DATABASE $INTERNAL_DB_NAME'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$INTERNAL_DB_NAME')\gexec
EOSQL

# Run initialization script
echo "Running database initialization..."
docker-compose exec -T postgres psql -U $INTERNAL_DB_ADMIN_USER -d $INTERNAL_DB_NAME < "${PROJECT_ROOT}/database/init_database.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database initialized successfully${NC}"
else
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi
echo ""

#==============================================================================
# Step 6: Install Python Dependencies
#==============================================================================
echo -e "${YELLOW}[6/7] Installing Python dependencies...${NC}"

cd "$PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
pip install -e . > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install Python dependencies${NC}"
    exit 1
fi
echo ""

#==============================================================================
# Step 7: Verify Installation
#==============================================================================
echo -e "${YELLOW}[7/7] Verifying installation...${NC}"

# Check database connection
PGPASSWORD=$INTERNAL_DB_PASSWORD docker-compose exec -T postgres psql -U $INTERNAL_DB_USER -d $INTERNAL_DB_NAME -c "\dt" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection verified${NC}"
else
    echo -e "${RED}✗ Cannot connect to database${NC}"
    exit 1
fi

# Count tables
TABLE_COUNT=$(PGPASSWORD=$INTERNAL_DB_PASSWORD docker-compose exec -T postgres psql -U $INTERNAL_DB_USER -d $INTERNAL_DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
echo -e "${GREEN}✓ Tables created: $TABLE_COUNT${NC}"

# Check default users
USER_COUNT=$(PGPASSWORD=$INTERNAL_DB_PASSWORD docker-compose exec -T postgres psql -U $INTERNAL_DB_USER -d $INTERNAL_DB_NAME -t -c "SELECT COUNT(*) FROM users;" | xargs)
echo -e "${GREEN}✓ Users created: $USER_COUNT${NC}"

echo ""

#==============================================================================
# Success Message
#==============================================================================
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}                   ✓ DataTruth Setup Complete!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Start the application:"
echo -e "   ${YELLOW}./bin/start.sh${NC}"
echo ""
echo "2. Access the application:"
echo -e "   API: ${YELLOW}http://localhost:$API_PORT${NC}"
echo -e "   Docs: ${YELLOW}http://localhost:$API_PORT/docs${NC}"
echo -e "   Health: ${YELLOW}http://localhost:$API_PORT/health${NC}"
echo ""
echo "3. Default credentials (CHANGE IMMEDIATELY!):"
echo -e "   Admin: ${YELLOW}username=admin, password=admin123${NC}"
echo -e "   Analyst: ${YELLOW}username=analyst, password=analyst123${NC}"
echo ""
echo -e "${BLUE}Important Security Notes:${NC}"
echo -e "   ${RED}• Change default passwords immediately${NC}"
echo -e "   ${RED}• Update SECRET_KEY and JWT_SECRET_KEY in .env${NC}"
echo -e "   ${RED}• Configure OPENAI_API_KEY for AI features${NC}"
echo -e "   ${RED}• Set proper CORS_ORIGINS for your domain${NC}"
echo ""
echo -e "${GREEN}==============================================================================${NC}"
