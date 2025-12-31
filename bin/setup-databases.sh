#!/bin/bash

# DataTruth Database Setup Script
# Sets up both internal (metadata) and external (demo) databases

set -e  # Exit on error

echo "=========================================="
echo "DataTruth Database Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment variables from .env${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Set connection parameters
export PGHOST=${INTERNAL_DB_HOST:-localhost}
export PGPORT=${INTERNAL_DB_PORT:-5432}
export PGUSER=${INTERNAL_DB_ADMIN_USER:-sentimarket}
export PGPASSWORD=${INTERNAL_DB_ADMIN_PASSWORD}

# Function to check if database exists
db_exists() {
    local dbname=$1
    psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbname'" 2>/dev/null | grep -q 1
}

# Function to create database if not exists
create_db() {
    local dbname=$1
    if db_exists "$dbname"; then
        echo -e "${YELLOW}Database '$dbname' already exists${NC}"
    else
        echo -e "${BLUE}Creating database '$dbname'...${NC}"
        createdb -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" "$dbname"
        echo -e "${GREEN}✓ Database '$dbname' created${NC}"
    fi
}

echo "=========================================="
echo "Step 1: Setup Internal Database (DataTruth Metadata)"
echo "=========================================="
echo ""
echo "This database stores:"
echo "  - Users, roles, permissions"
echo "  - Connection configurations"
echo "  - Field mappings"
echo "  - Query history and audit logs"
echo ""

# Create internal database
INTERNAL_DB=${INTERNAL_DB_NAME:-datatruth}
create_db "$INTERNAL_DB"

# Note: Since we're using your existing PostgreSQL user, we skip creating new users
echo -e "${BLUE}Using existing PostgreSQL user: $PGUSER${NC}"

# Grant privileges to yourself on the database
psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" postgres -c "GRANT ALL PRIVILEGES ON DATABASE $INTERNAL_DB TO $PGUSER;" 2>/dev/null || true

# Apply internal schema
echo -e "${BLUE}Applying internal database schema...${NC}"
psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" "$INTERNAL_DB" -f database/internal-schema.sql
echo -e "${GREEN}✓ Internal schema applied${NC}"

# Seed internal database
echo -e "${BLUE}Seeding internal database...${NC}"
psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" "$INTERNAL_DB" -f database/internal-seed.sql
echo -e "${GREEN}✓ Internal database seeded${NC}"

echo ""
echo -e "${GREEN}✓ Internal database setup complete!${NC}"
echo ""

echo "=========================================="
echo "Step 2: Setup External Demo Database (Optional)"
echo "=========================================="
echo ""
echo "This database contains SAMPLE data for testing:"
echo "  - Transactions, agents, clients"
echo "  - Typical business data structure"
echo "  - Users will query THIS database, not the internal one"
echo ""
echo "In production, users configure their own external databases via UI."
echo ""

read -p "Do you want to setup the demo external database? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create external demo database
    EXTERNAL_DB=${EXTERNAL_DEMO_DB_NAME:-datatruth_external}
    create_db "$EXTERNAL_DB"
    
    # Grant privileges to yourself
    psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" postgres -c "GRANT ALL PRIVILEGES ON DATABASE $EXTERNAL_DB TO $PGUSER;" 2>/dev/null || true
    
    # Apply external schema
    echo -e "${BLUE}Applying external database schema...${NC}"
    psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" "$EXTERNAL_DB" -f database/schema.sql
    echo -e "${GREEN}✓ External schema applied${NC}"
    
    # Seed external database
    echo -e "${BLUE}Seeding external database with sample data...${NC}"
    psql -U "$PGUSER" -h "$PGHOST" -p "$PGPORT" "$EXTERNAL_DB" -f database/seed.sql
    echo -e "${GREEN}✓ External database seeded${NC}"
    
    echo ""
    echo -e "${GREEN}✓ External demo database setup complete!${NC}"
else
    echo -e "${YELLOW}Skipped external demo database setup${NC}"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Databases Created:"
echo "  1. ${GREEN}$INTERNAL_DB${NC} - DataTruth internal metadata"
echo "     Tables: users, roles, permissions, connections, field_mappings, etc."
echo ""
echo "  2. ${GREEN}${EXTERNAL_DEMO_DB_NAME:-datatruth_external}${NC} - External demo database (optional)"
echo "     Tables: transactions, agents, clients, companies"
echo ""
echo "Default Users (Internal Database):"
echo "  Admin:   username=${GREEN}admin${NC}   password=${YELLOW}admin123${NC}   (CHANGE IN PRODUCTION!)"
echo "  Analyst: username=${GREEN}analyst${NC} password=${YELLOW}analyst123${NC}"
echo "  Viewer:  username=${GREEN}viewer${NC}  password=${YELLOW}viewer123${NC}"
echo ""
echo "Next Steps:"
echo "  1. Start the backend: ${BLUE}./start.sh${NC}"
echo "  2. Start the frontend: ${BLUE}cd frontend && npm run dev${NC}"
echo "  3. Login with: ${GREEN}admin${NC} / ${YELLOW}admin123${NC}"
echo "  4. Go to 'Connections' tab"
echo "  5. Create a connection to: ${GREEN}${EXTERNAL_DEMO_DB_NAME:-datatruth_external}${NC}"
echo "  6. Discover schema and start querying!"
echo ""
echo "Verify Setup:"
echo "  ${BLUE}psql $INTERNAL_DB -c '\\dt'${NC}  # List internal tables"
echo "  ${BLUE}psql $INTERNAL_DB -c 'SELECT username FROM users;'${NC}  # List users"
echo "  ${BLUE}psql ${EXTERNAL_DEMO_DB_NAME:-datatruth_external} -c '\\dt'${NC}  # List external tables"
echo ""
echo "=========================================="
