#!/bin/bash

# DataTruth - Benchmark Script
# Run performance benchmarks

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Virtual environment not found. Run ./start.sh first${NC}"
    exit 1
fi

echo -e "${BLUE}⚡ Running Performance Benchmarks${NC}"
echo ""

# Check if services are running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  PostgreSQL not running. Starting services...${NC}"
    docker-compose up -d postgres redis
    sleep 3
fi

echo -e "${GREEN}Starting benchmark suite...${NC}"
echo ""
python benchmark_performance.py

echo ""
echo -e "${GREEN}✓ Benchmarks complete${NC}"
