#!/bin/bash

# DataTruth - Database Restore Script
# Restores a database from a backup file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DataTruth - Database Restore${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

source .env

# Set backup directory
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Determine compose file
COMPOSE_FILE="docker-compose.yml"
if [ "$ENVIRONMENT" == "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <backup_file>${NC}"
    echo ""
    echo -e "${BLUE}Available backups:${NC}"
    if [ -d "$BACKUP_DIR" ]; then
        ls -1t "$BACKUP_DIR"/datatruth_backup_*.sql.gz 2>/dev/null | head -10 | sed 's/^/  /' || echo "  (No backups found)"
    else
        echo "  (Backup directory not found)"
    fi
    echo ""
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if PostgreSQL is running
echo -e "${BLUE}🔍 Checking database connection...${NC}"
if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U datatruth_app > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL is not running${NC}"
    echo -e "${YELLOW}Start services with: ./bin/start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Database connected${NC}"
echo ""

# Show backup info
BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
BACKUP_DATE=$(ls -lh "$BACKUP_FILE" | awk '{print $6 " " $7 " " $8}')

echo -e "${BLUE}📦 Restore Configuration:${NC}"
echo "  Backup File: $BACKUP_FILE"
echo "  File Size: $BACKUP_SIZE"
echo "  File Date: $BACKUP_DATE"
echo "  Database: ${INTERNAL_DB_NAME:-datatruth_internal}"
echo "  User: ${INTERNAL_DB_ADMIN_USER:-datatruth_admin}"
echo ""

# Warning
echo -e "${RED}⚠️  WARNING ⚠️${NC}"
echo -e "${RED}This will DROP and RECREATE the database!${NC}"
echo -e "${RED}All current data will be LOST!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

# Create a safety backup before restore
echo -e "${BLUE}💾 Creating safety backup before restore...${NC}"
SAFETY_BACKUP="$BACKUP_DIR/datatruth_before_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "${INTERNAL_DB_ADMIN_USER:-datatruth_admin}" \
    "${INTERNAL_DB_NAME:-datatruth_internal}" \
    --clean --if-exists --create \
    | gzip > "$SAFETY_BACKUP" 2>/dev/null || true

if [ -f "$SAFETY_BACKUP" ]; then
    echo -e "${GREEN}✓ Safety backup created: $SAFETY_BACKUP${NC}"
else
    echo -e "${YELLOW}⚠️  Could not create safety backup (database may not exist yet)${NC}"
fi
echo ""

# Terminate active connections
echo -e "${BLUE}🔌 Terminating active connections...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${INTERNAL_DB_ADMIN_USER:-datatruth_admin}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${INTERNAL_DB_NAME:-datatruth_internal}' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Connections terminated${NC}"
echo ""

# Restore database
echo -e "${BLUE}♻️  Restoring database...${NC}"
gunzip < "$BACKUP_FILE" | docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${INTERNAL_DB_ADMIN_USER:-datatruth_admin}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database restored successfully${NC}"
else
    echo -e "${RED}❌ Restore failed${NC}"
    if [ -f "$SAFETY_BACKUP" ]; then
        echo -e "${YELLOW}Safety backup available at: $SAFETY_BACKUP${NC}"
    fi
    exit 1
fi

# Verify restore
echo ""
echo -e "${BLUE}🔍 Verifying restore...${NC}"

# Check database exists
DB_EXISTS=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${INTERNAL_DB_ADMIN_USER:-datatruth_admin}" -d postgres -t -c \
    "SELECT 1 FROM pg_database WHERE datname='${INTERNAL_DB_NAME:-datatruth_internal}';" | xargs)

if [ "$DB_EXISTS" == "1" ]; then
    echo -e "${GREEN}✓ Database exists${NC}"
    
    # Count tables
    TABLE_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U datatruth_app -d "${INTERNAL_DB_NAME:-datatruth_internal}" -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | xargs)
    
    if [ -n "$TABLE_COUNT" ]; then
        echo -e "${GREEN}✓ Tables: $TABLE_COUNT${NC}"
    fi
    
    # Count users
    USER_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U datatruth_app -d "${INTERNAL_DB_NAME:-datatruth_internal}" -t -c \
        "SELECT count(*) FROM users;" 2>/dev/null | xargs)
    
    if [ -n "$USER_COUNT" ]; then
        echo -e "${GREEN}✓ Users: $USER_COUNT${NC}"
    fi
else
    echo -e "${RED}✗ Database not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Restore Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Remove safety backup if restore was successful
if [ -f "$SAFETY_BACKUP" ]; then
    read -p "Remove safety backup? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$SAFETY_BACKUP"
        echo -e "${GREEN}✓ Safety backup removed${NC}"
    else
        echo -e "${YELLOW}Safety backup kept: $SAFETY_BACKUP${NC}"
    fi
fi

echo ""
