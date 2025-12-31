#!/bin/bash

# DataTruth - Service Status
# Shows status of all services and system health

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

clear
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}DataTruth - Service Status${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check which compose file to use
COMPOSE_FILE="docker-compose.yml"
if [ -f .env ]; then
    source .env
    if [ "$ENVIRONMENT" == "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        echo -e "${BLUE}Environment: ${GREEN}Production${NC}"
    else
        echo -e "${BLUE}Environment: ${YELLOW}Development${NC}"
    fi
else
    echo -e "${RED}⚠️  No .env file found${NC}"
fi
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Show container status
echo -e "${BLUE}📦 Container Status:${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" ps
echo ""

# Check individual services
echo -e "${BLUE}🔍 Service Health Checks:${NC}"
echo ""

# PostgreSQL
echo -n "  PostgreSQL: "
if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U datatruth_app > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    
    # Get database info
    DB_SIZE=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U datatruth_app -d datatruth_internal -t -c \
        "SELECT pg_size_pretty(pg_database_size('datatruth_internal'));" 2>/dev/null | xargs)
    
    CONNECTIONS=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U datatruth_app -d datatruth_internal -t -c \
        "SELECT count(*) FROM pg_stat_activity WHERE datname='datatruth_internal';" 2>/dev/null | xargs)
    
    if [ -n "$DB_SIZE" ]; then
        echo "              Size: $DB_SIZE"
    fi
    if [ -n "$CONNECTIONS" ]; then
        echo "              Active Connections: $CONNECTIONS"
    fi
else
    echo -e "${RED}✗ Not Running${NC}"
fi
echo ""

# Redis
echo -n "  Redis: "
if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    
    # Get Redis info
    REDIS_MEMORY=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli info memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' 2>/dev/null)
    
    REDIS_KEYS=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli dbsize | tr -d '\r' 2>/dev/null)
    
    if [ -n "$REDIS_MEMORY" ]; then
        echo "         Memory: $REDIS_MEMORY"
    fi
    if [ -n "$REDIS_KEYS" ]; then
        echo "         Keys: $REDIS_KEYS"
    fi
else
    echo -e "${RED}✗ Not Running${NC}"
fi
echo ""

# API
echo -n "  API: "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    
    # Get API health details
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    
    if [ -n "$HEALTH_RESPONSE" ]; then
        API_STATUS=$(echo $HEALTH_RESPONSE | jq -r '.status' 2>/dev/null || echo "unknown")
        echo "       Status: $API_STATUS"
        
        # Show component statuses if available
        DB_STATUS=$(echo $HEALTH_RESPONSE | jq -r '.checks.database.status' 2>/dev/null)
        if [ "$DB_STATUS" != "null" ] && [ -n "$DB_STATUS" ]; then
            echo "       Database: $DB_STATUS"
        fi
        
        SYS_STATUS=$(echo $HEALTH_RESPONSE | jq -r '.checks.system.status' 2>/dev/null)
        if [ "$SYS_STATUS" != "null" ] && [ -n "$SYS_STATUS" ]; then
            echo "       System: $SYS_STATUS"
        fi
    fi
else
    echo -e "${RED}✗ Not Running${NC}"
fi
echo ""

# Nginx (if production)
if [ "$ENVIRONMENT" == "production" ]; then
    echo -n "  Nginx: "
    if docker-compose -f "$COMPOSE_FILE" ps nginx | grep -q "Up"; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Running${NC}"
    fi
    echo ""
fi

# System resources
echo -e "${BLUE}💻 System Resources:${NC}"
echo ""

# CPU usage
CPU_USAGE=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}" | grep -E "postgres|redis|api|nginx" 2>/dev/null || echo "")
if [ -n "$CPU_USAGE" ]; then
    echo "$CPU_USAGE" | sed 's/^/  /'
else
    echo "  (Unable to get CPU stats)"
fi
echo ""

# Memory usage
MEM_USAGE=$(docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | grep -E "postgres|redis|api|nginx" 2>/dev/null || echo "")
if [ -n "$MEM_USAGE" ]; then
    echo "$MEM_USAGE" | sed 's/^/  /'
else
    echo "  (Unable to get memory stats)"
fi
echo ""

# Disk usage
echo -e "${BLUE}💾 Disk Usage:${NC}"
echo ""
du -sh data/ logs/ 2>/dev/null | sed 's/^/  /' || echo "  (Unable to get disk usage)"
echo ""

# Recent logs
echo -e "${BLUE}📝 Recent Logs (last 10 lines):${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" logs --tail=10 api 2>/dev/null | sed 's/^/  /'
echo ""

# Quick stats
echo -e "${BLUE}📊 Quick Stats:${NC}"
echo ""

# Count users
USER_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U datatruth_app -d datatruth_internal -t -c \
    "SELECT count(*) FROM users;" 2>/dev/null | xargs)
if [ -n "$USER_COUNT" ]; then
    echo "  Users: $USER_COUNT"
fi

# Count connections
CONN_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U datatruth_app -d datatruth_internal -t -c \
    "SELECT count(*) FROM connections;" 2>/dev/null | xargs)
if [ -n "$CONN_COUNT" ]; then
    echo "  Connections: $CONN_COUNT"
fi

# Count calculated metrics
METRIC_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U datatruth_app -d datatruth_internal -t -c \
    "SELECT count(*) FROM calculated_metrics;" 2>/dev/null | xargs)
if [ -n "$METRIC_COUNT" ]; then
    echo "  Calculated Metrics: $METRIC_COUNT"
fi

# Count user activities (if available)
ACTIVITY_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U datatruth_app -d datatruth_internal -t -c \
    "SELECT count(*) FROM user_activity WHERE created_at > NOW() - INTERVAL '24 hours';" 2>/dev/null | xargs)
if [ -n "$ACTIVITY_COUNT" ]; then
    echo "  Activities (24h): $ACTIVITY_COUNT"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${BLUE}🔗 Access Points:${NC}"
echo -e "  API:      ${GREEN}http://localhost:8000${NC}"
echo -e "  Docs:     ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  Health:   ${GREEN}http://localhost:8000/health${NC}"
echo -e "  Metrics:  ${GREEN}http://localhost:8000/metrics${NC}"
echo ""
echo -e "${BLUE}💡 Useful Commands:${NC}"
echo -e "  View logs:    ${YELLOW}docker-compose -f $COMPOSE_FILE logs -f [service]${NC}"
echo -e "  Restart:      ${YELLOW}docker-compose -f $COMPOSE_FILE restart [service]${NC}"
echo -e "  Shell access: ${YELLOW}docker-compose -f $COMPOSE_FILE exec [service] /bin/bash${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
