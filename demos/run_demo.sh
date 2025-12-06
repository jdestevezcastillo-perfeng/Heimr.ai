#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

# =============================================================================
# Heimr Demo - Complete Load Testing Showcase
# =============================================================================
# This script orchestrates a full demo of Heimr's capabilities:
# 1. Deploys the 3-tier architecture (Frontend → API → DB)
# 2. Runs load tests with k6, Locust (JMeter optional)
# 3. Analyzes results with Heimr
# 4. Generates comparison reports
#
# Prerequisites:
# - kubectl configured with a running K8s cluster
# - k6 installed (https://k6.io/docs/getting-started/installation/)
# - locust installed (pip install locust)
# - Heimr installed (pip install .)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/load-tests/results/demo_$(date +%Y%m%d_%H%M%S)"

# Configuration
TEST_DURATION="${TEST_DURATION:-5m}"
K6_VUS="${K6_VUS:-10}"
LOCUST_USERS="${LOCUST_USERS:-10}"
API_URL="${API_URL:-http://localhost:30808}"

# Banner
echo ""
echo -e "${CYAN}${BOLD}"
cat << 'EOF'
   ▄▄▄  ▄▄▄                                    
  █▀██  ██                                     
    ██  ██         ▀▀ ▄        ▄             ▀▀
    ██████   ▄█▀█▄ ██ ███▄███▄ ████▄   ▄▀▀█▄ ██
    ██  ██   ██▄█▀ ██ ██ ██ ██ ██      ▄█▀██ ██
  ▀██▀  ▀██▄▄▀█▄▄▄▄██▄██ ██ ▀█▄█▀  ██ ▄▀█▄██▄██
                                                
  Complete Load Testing Demo
EOF
echo -e "${NC}"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"
echo -e "${GREEN}✅ Results will be saved to: ${RESULTS_DIR}${NC}"
echo ""

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📋 Step 1: Checking Prerequisites${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check kubectl
if command -v kubectl &> /dev/null; then
    echo -e "${GREEN}✅ kubectl found${NC}"
else
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check k6
if command -v k6 &> /dev/null; then
    echo -e "${GREEN}✅ k6 found${NC}"
    HAS_K6=true
else
    echo -e "${YELLOW}⚠️ k6 not found. k6 tests will be skipped.${NC}"
    HAS_K6=false
fi

# Check locust
if command -v locust &> /dev/null; then
    echo -e "${GREEN}✅ locust found${NC}"
    HAS_LOCUST=true
else
    echo -e "${YELLOW}⚠️ locust not found. Locust tests will be skipped.${NC}"
    HAS_LOCUST=false
fi

# Check heimr
HEIMR_CMD="heimr"
if [ -f "$PROJECT_ROOT/.venv/bin/heimr" ]; then
    HEIMR_CMD="$PROJECT_ROOT/.venv/bin/heimr"
    echo -e "${GREEN}✅ heimr found (venv)${NC}"
elif command -v heimr &> /dev/null; then
    echo -e "${GREEN}✅ heimr found${NC}"
else
    HEIMR_CMD="python3 -m heimr.cli"
    echo -e "${YELLOW}⚠️ Using python3 -m heimr.cli${NC}"
fi

echo ""

# =============================================================================
# Step 2: Deploy Infrastructure (Optional)
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🚀 Step 2: Infrastructure Check${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if API is reachable
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is reachable at $API_URL${NC}"
else
    echo -e "${YELLOW}⚠️ API not reachable. Attempting to deploy...${NC}"
    
    if kubectl get namespace heimr-demo > /dev/null 2>&1; then
        echo -e "${CYAN}ℹ️ Namespace exists, restarting deployments...${NC}"
        kubectl rollout restart deployment -n heimr-demo
    else
        echo -e "${CYAN}ℹ️ Deploying demo infrastructure...${NC}"
        kubectl apply -f "$PROJECT_ROOT/k8s/demo/"
    fi
    
    echo -e "${YELLOW}Waiting for pods to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app=heimr-demo-api -n heimr-demo --timeout=120s || true
    
    # Port forward if needed
    echo -e "${CYAN}ℹ️ Setting up port forwarding...${NC}"
    kubectl port-forward svc/heimr-demo-api 30808:8080 -n heimr-demo &
    PORT_FORWARD_PID=$!
    sleep 3
fi

echo ""

# =============================================================================
# Step 3: Run k6 Load Test
# =============================================================================
if [ "$HAS_K6" = true ]; then
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}⚡ Step 3: Running k6 Load Test${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    K6_RESULT="$RESULTS_DIR/k6_results.json"
    
    echo -e "${CYAN}Running: k6 run --out json=$K6_RESULT $PROJECT_ROOT/load-tests/k6/demo-test.js${NC}"
    echo ""
    
    BASE_URL="$API_URL" k6 run \
        --out "json=$K6_RESULT" \
        "$PROJECT_ROOT/load-tests/k6/demo-test.js" || true
    
    echo ""
    echo -e "${GREEN}✅ k6 results saved to: $K6_RESULT${NC}"
    echo ""
fi

# =============================================================================
# Step 4: Run Locust Load Test
# =============================================================================
if [ "$HAS_LOCUST" = true ]; then
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🦗 Step 4: Running Locust Load Test${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    LOCUST_RESULT="$RESULTS_DIR/locust"
    
    echo -e "${CYAN}Running: locust -f locustfile.py --headless -u $LOCUST_USERS -r 1 --run-time $TEST_DURATION --csv=$LOCUST_RESULT${NC}"
    echo ""
    
    cd "$PROJECT_ROOT/load-tests/locust"
    locust -f locustfile.py \
        --headless \
        --host "$API_URL" \
        -u "$LOCUST_USERS" \
        -r 1 \
        --run-time "$TEST_DURATION" \
        --csv="$LOCUST_RESULT" || true
    cd "$PROJECT_ROOT"
    
    echo ""
    echo -e "${GREEN}✅ Locust results saved to: ${LOCUST_RESULT}_stats_history.csv${NC}"
    echo ""
fi

# =============================================================================
# Step 5: Analyze Results with Heimr
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🔍 Step 5: Analyzing Results with Heimr${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Analyze k6 results
if [ -f "$RESULTS_DIR/k6_results.json" ]; then
    echo -e "${CYAN}Analyzing k6 results...${NC}"
    $HEIMR_CMD analyze "$RESULTS_DIR/k6_results.json" \
        --explain \
        --output "$RESULTS_DIR/heimr_k6_report.md" || true
    echo ""
fi

# Analyze Locust results
if [ -f "${RESULTS_DIR}/locust_stats_history.csv" ]; then
    echo -e "${CYAN}Analyzing Locust results...${NC}"
    $HEIMR_CMD analyze "${RESULTS_DIR}/locust_stats_history.csv" \
        --explain \
        --output "$RESULTS_DIR/heimr_locust_report.md" || true
    echo ""
fi

# =============================================================================
# Step 6: Summary
# =============================================================================
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✅ Demo Complete!${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Results saved to:${NC} ${GREEN}$RESULTS_DIR${NC}"
echo ""
echo -e "  ${BOLD}Files generated:${NC}"
ls -la "$RESULTS_DIR" | grep -E "\.(json|csv|md)$" | awk '{print "    📄 " $NF}'
echo ""
echo -e "  ${BOLD}View reports:${NC}"
echo -e "    cat \"$RESULTS_DIR/heimr_k6_report.md\""
echo -e "    cat \"$RESULTS_DIR/heimr_locust_report.md\""
echo ""

# Cleanup port forwarding if we started it
if [ -n "$PORT_FORWARD_PID" ]; then
    kill $PORT_FORWARD_PID 2>/dev/null || true
fi
