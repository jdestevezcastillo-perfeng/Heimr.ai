#!/bin/bash
# Heimr Demo Pre-Flight Checks
# Verifies all systems are ready before running load tests

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         HEIMR DEMO PRE-FLIGHT CHECKS                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_passed=0
check_failed=0

# Function to check service
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Checking $name... "
    if curl -sf "$url" | grep -q "$expected" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
        ((check_passed++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((check_failed++))
        return 1
    fi
}

# Function to check command
check_command() {
    local name=$1
    local cmd=$2
    
    echo -n "Checking $name... "
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓ OK${NC} ($(which $cmd))"
        ((check_passed++))
        return 0
    else
        echo -e "${RED}✗ NOT FOUND${NC}"
        ((check_failed++))
        return 1
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. REQUIRED TOOLS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_command "Heimr CLI" "heimr"
check_command "k6 Load Testing" "k6"
check_command "Docker" "docker"
check_command "curl" "curl"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. HEIMR CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -n "Heimr version... "
heimr --version 2>&1 | head -1 || echo -e "${RED}✗ FAILED${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. LLM SERVICE (Ollama)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -n "Ollama service... "
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ RUNNING${NC}"
    ((check_passed++))
    echo -n "Available models... "
    models=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ', ' | sed 's/,$//')
    if [ -n "$models" ]; then
        echo -e "${GREEN}$models${NC}"
    else
        echo -e "${YELLOW}⚠ No models found${NC}"
    fi
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    echo -e "${YELLOW}  → Start with: systemctl start ollama${NC}"
    ((check_failed++))
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. OBSERVABILITY STACK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_service "Prometheus" "http://localhost:9090/-/healthy" "Prometheus"
check_service "Loki" "http://localhost:3100/ready" "ready"
check_service "Tempo" "http://localhost:3200/ready" "ready"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. TARGET APPLICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -n "Petstore API... "
if curl -sf http://localhost:8080/actuator/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ RUNNING${NC}"
    ((check_passed++))
    
    # Check database connection
    echo -n "Database connection... "
    health=$(curl -s http://localhost:8080/actuator/health)
    if echo "$health" | grep -q '"status":"UP"'; then
        echo -e "${GREEN}✓ HEALTHY${NC}"
        ((check_passed++))
    else
        echo -e "${YELLOW}⚠ DEGRADED${NC}"
    fi
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    echo -e "${YELLOW}  → Check: docker ps | grep petstore${NC}"
    ((check_failed++))
fi

# Check PostgreSQL
echo -n "PostgreSQL... "
if docker ps | grep -q petstore-db; then
    echo -e "${GREEN}✓ RUNNING${NC}"
    ((check_passed++))
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    ((check_failed++))
fi

# Check PostgreSQL Exporter
echo -n "PostgreSQL Exporter... "
if curl -sf http://localhost:9187/metrics > /dev/null 2>&1; then
    echo -e "${GREEN}✓ RUNNING${NC}"
    ((check_passed++))
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    ((check_failed++))
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. PROMETHEUS TARGETS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if curl -sf http://localhost:9090/api/v1/targets > /dev/null 2>&1; then
    targets=$(curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[^"]*"' | cut -d'"' -f4)
    up_count=$(echo "$targets" | grep -c "up" || echo "0")
    down_count=$(echo "$targets" | grep -c "down" || echo "0")
    
    echo "Active targets: ${GREEN}$up_count UP${NC}, ${RED}$down_count DOWN${NC}"
    
    if [ "$down_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠ Some targets are down - metrics may be incomplete${NC}"
    fi
else
    echo -e "${RED}✗ Cannot query Prometheus targets${NC}"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Passed: ${GREEN}$check_passed${NC}"
echo -e "Failed: ${RED}$check_failed${NC}"
echo ""

if [ $check_failed -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL SYSTEMS GO - Ready for load testing!               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ SOME CHECKS FAILED - Please fix issues before testing  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
