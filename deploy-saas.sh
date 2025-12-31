#!/bin/bash

# DataTruth - SaaS Deployment Launcher
# One-command deployment with web-based setup wizard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║              DataTruth - SaaS Deployment                ║"
echo "║          Ship and Go - No Configuration Needed!         ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo -e "${YELLOW}Please install Docker: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo -e "${YELLOW}Please install Docker Compose: https://docs.docker.com/compose/install/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker and try again${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

echo ""

# Check if already deployed
if docker-compose -f docker-compose.saas.yml ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  DataTruth services are already running${NC}"
    echo ""
    echo "Options:"
    echo "  1) Restart services"
    echo "  2) Stop and redeploy"
    echo "  3) Exit"
    read -p "Choose an option (1-3): " -n 1 -r
    echo ""
    
    case $REPLY in
        1)
            echo -e "${BLUE}🔄 Restarting services...${NC}"
            docker-compose -f docker-compose.saas.yml restart
            ;;
        2)
            echo -e "${BLUE}🛑 Stopping services...${NC}"
            docker-compose -f docker-compose.saas.yml down
            echo -e "${BLUE}🚀 Deploying fresh...${NC}"
            docker-compose -f docker-compose.saas.yml up -d --build
            ;;
        3)
            echo -e "${GREEN}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            exit 1
            ;;
    esac
else
    # Deploy
    echo -e "${BLUE}🚀 Deploying DataTruth...${NC}"
    echo ""
    echo "This will:"
    echo "  • Pull required Docker images"
    echo "  • Build application containers"
    echo "  • Start PostgreSQL, Redis, API, and Frontend"
    echo "  • Launch setup wizard at http://localhost:3000"
    echo ""
    read -p "Continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
    
    # Create data directory
    mkdir -p data logs backups
    
    # Start services
    echo ""
    echo -e "${BLUE}📦 Starting services...${NC}"
    docker-compose -f docker-compose.saas.yml up -d --build
fi

# Wait for services
echo ""
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check PostgreSQL
echo -n "  PostgreSQL... "
for i in {1..30}; do
    if docker-compose -f docker-compose.saas.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    sleep 1
done

# Check Redis
echo -n "  Redis... "
for i in {1..30}; do
    if docker-compose -f docker-compose.saas.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        break
    fi
    sleep 1
done

# Check API
echo -n "  API... "
API_READY=false
for i in {1..60}; do
    if curl -s http://localhost:8000/api/setup/status > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        API_READY=true
        break
    fi
    sleep 1
done

if [ "$API_READY" = false ]; then
    echo -e "${RED}✗${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  API took longer than expected to start${NC}"
    echo -e "${YELLOW}Check logs: docker-compose -f docker-compose.saas.yml logs api${NC}"
fi

# Check Frontend
echo -n "  Frontend... "
FRONTEND_READY=false
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        FRONTEND_READY=true
        break
    fi
    sleep 1
done

if [ "$FRONTEND_READY" = false ]; then
    echo -e "${YELLOW}⚠️ Frontend not ready yet${NC}"
fi

# Success message
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║            ✅  DataTruth Deployed Successfully!          ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check setup status
SETUP_STATUS=$(curl -s http://localhost:8000/api/setup/status 2>/dev/null || echo '{"needs_setup": true}')
NEEDS_SETUP=$(echo $SETUP_STATUS | grep -q '"needs_setup":true' && echo "true" || echo "false")

if [ "$NEEDS_SETUP" = "true" ]; then
    echo -e "${CYAN}📝 Setup Required${NC}"
    echo ""
    echo "Your DataTruth instance is ready for first-time setup!"
    echo ""
    echo -e "${BLUE}🌐 Access Points:${NC}"
    echo -e "  Setup Wizard:  ${GREEN}http://localhost:3000${NC}"
    echo -e "  API:           ${GREEN}http://localhost:8000${NC}"
    echo -e "  API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${CYAN}📋 Next Steps:${NC}"
    echo "  1. Open http://localhost:3000 in your browser"
    echo "  2. Follow the setup wizard"
    echo "  3. Provide:"
    echo "     • Database connection (default: postgres/postgres)"
    echo "     • OpenAI API key (get from platform.openai.com)"
    echo "     • Admin credentials (create your login)"
    echo "  4. Complete setup and start querying!"
    echo ""
    echo -e "${YELLOW}💡 Tip: Have your OpenAI API key ready!${NC}"
else
    echo -e "${CYAN}✅ Already Configured${NC}"
    echo ""
    echo -e "${BLUE}🌐 Access Points:${NC}"
    echo -e "  Application:   ${GREEN}http://localhost:3000${NC}"
    echo -e "  API:           ${GREEN}http://localhost:8000${NC}"
    echo -e "  API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  Health:        ${GREEN}http://localhost:8000/health${NC}"
    echo ""
    echo -e "${CYAN}📋 Login and Start Querying!${NC}"
fi

echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo -e "  View logs:     ${YELLOW}docker-compose -f docker-compose.saas.yml logs -f${NC}"
echo -e "  Stop:          ${YELLOW}docker-compose -f docker-compose.saas.yml stop${NC}"
echo -e "  Restart:       ${YELLOW}docker-compose -f docker-compose.saas.yml restart${NC}"
echo -e "  Status:        ${YELLOW}docker-compose -f docker-compose.saas.yml ps${NC}"
echo ""

# Open browser (optional)
if command -v open &> /dev/null; then
    read -p "Open setup wizard in browser? (Y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if [ "$NEEDS_SETUP" = "true" ]; then
            open http://localhost:3000
        else
            open http://localhost:3000
        fi
    fi
elif command -v xdg-open &> /dev/null; then
    if [ "$NEEDS_SETUP" = "true" ]; then
        xdg-open http://localhost:3000 &> /dev/null
    fi
fi

echo -e "${GREEN}🎉 Deployment complete! Happy querying!${NC}"
echo ""
