#!/bin/bash

# DataTruth - Database Backup Script
# Creates a compressed backup of the PostgreSQL database

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
echo -e "${BLUE}DataTruth - Database Backup${NC}"
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
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/datatruth_backup_$TIMESTAMP.sql.gz"

# Determine compose file
COMPOSE_FILE="docker-compose.yml"
if [ "$ENVIRONMENT" == "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

echo -e "${BLUE}📦 Backup Configuration:${NC}"
echo "  Directory: $BACKUP_DIR"
echo "  File: datatruth_backup_$TIMESTAMP.sql.gz"
echo "  Database: ${INTERNAL_DB_NAME:-datatruth_internal}"
echo "  User: ${INTERNAL_DB_ADMIN_USER:-datatruth_admin}"
echo ""

# Check if PostgreSQL is running
echo -e "${BLUE}🔍 Checking database connection...${NC}"
if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U datatruth_app > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL is not running${NC}"
    echo -e "${YELLOW}Start services with: ./bin/start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Database connected${NC}"
echo ""

# Create backup
echo -e "${BLUE}💾 Creating backup...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "${INTERNAL_DB_ADMIN_USER:-datatruth_admin}" \
    "${INTERNAL_DB_NAME:-datatruth_internal}" \
    --clean --if-exists --create \
    | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo -e "${GREEN}✅ Backup created successfully${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Backup retention (keep last N backups)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
echo ""
echo -e "${BLUE}🗑️  Cleaning old backups (older than $RETENTION_DAYS days)...${NC}"
DELETED_COUNT=$(find "$BACKUP_DIR" -name "datatruth_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l | xargs)
if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Deleted $DELETED_COUNT old backup(s)${NC}"
else
    echo -e "${GREEN}✓ No old backups to delete${NC}"
fi

# Show existing backups
echo ""
echo -e "${BLUE}📋 Recent Backups:${NC}"
ls -lth "$BACKUP_DIR"/datatruth_backup_*.sql.gz 2>/dev/null | head -5 | awk '{print "  " $9 " (" $5 " - " $6 " " $7 " " $8 ")"}' || echo "  (No backups found)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Backup Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}💡 To restore this backup:${NC}"
echo -e "  ${YELLOW}gunzip < $BACKUP_FILE | \\${NC}"
echo -e "  ${YELLOW}docker-compose -f $COMPOSE_FILE exec -T postgres \\${NC}"
echo -e "  ${YELLOW}psql -U ${INTERNAL_DB_ADMIN_USER:-datatruth_admin}${NC}"
echo ""
echo -e "${BLUE}📤 To upload to cloud storage:${NC}"
echo -e "  AWS S3:   ${YELLOW}aws s3 cp $BACKUP_FILE s3://your-bucket/backups/${NC}"
echo -e "  GCS:      ${YELLOW}gsutil cp $BACKUP_FILE gs://your-bucket/backups/${NC}"
echo -e "  Azure:    ${YELLOW}az storage blob upload --file $BACKUP_FILE --container backups${NC}"
echo ""
