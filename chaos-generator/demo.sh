#!/bin/bash
# Demo script to showcase all chaos scenarios

set -e

CHAOS_URL="http://localhost:8000"
COLORS=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Chaos Generator - Interactive Demo                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section headers
print_header() {
    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to activate a scenario
activate_scenario() {
    local scenario=$1
    local description=$2
    
    print_header "Scenario: $scenario"
    echo -e "${YELLOW}Description:${NC} $description"
    echo ""
    
    echo -e "${BLUE}→ Activating scenario...${NC}"
    curl -s -X POST "$CHAOS_URL/chaos/scenario/$scenario" | jq -r '.message'
    echo ""
    
    sleep 1
}

# Function to generate load and show results
generate_load() {
    local requests=${1:-20}
    local description=${2:-"Generating load"}
    
    echo -e "${BLUE}→ $description (${requests} requests)...${NC}"
    echo ""
    
    # Make requests and collect response times and status codes
    local success=0
    local errors=0
    local total_time=0
    
    for i in $(seq 1 $requests); do
        response=$(curl -s -w "\n%{http_code}\n%{time_total}" -o /dev/null "$CHAOS_URL/api/work")
        status=$(echo "$response" | sed -n '1p')
        time=$(echo "$response" | sed -n '2p')
        
        if [ "$status" = "200" ]; then
            ((success++))
            echo -e "  ${GREEN}✓${NC} Request $i: ${status} (${time}s)"
        else
            ((errors++))
            echo -e "  ${RED}✗${NC} Request $i: ${status} (${time}s)"
        fi
        
        # Small delay between requests
        sleep 0.05
    done
    
    echo ""
    echo -e "${CYAN}Results:${NC}"
    echo -e "  Success: ${GREEN}$success${NC} / $requests"
    echo -e "  Errors:  ${RED}$errors${NC} / $requests"
    
    if [ $errors -gt 0 ]; then
        error_rate=$(awk "BEGIN {printf \"%.1f\", ($errors/$requests)*100}")
        echo -e "  Error Rate: ${YELLOW}${error_rate}%${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}⏸  Pausing for 5 seconds to observe metrics...${NC}"
    sleep 5
}

# Check if services are running
print_header "Pre-flight Check"
echo -e "${BLUE}→ Checking Chaos Generator...${NC}"
if curl -s "$CHAOS_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ Chaos Generator is healthy${NC}"
else
    echo -e "${RED}✗ Chaos Generator is not responding${NC}"
    echo -e "${YELLOW}Run: docker compose up -d${NC}"
    exit 1
fi

echo -e "${BLUE}→ Checking Prometheus...${NC}"
if curl -s "http://localhost:9090/-/healthy" > /dev/null; then
    echo -e "${GREEN}✓ Prometheus is healthy${NC}"
else
    echo -e "${RED}✗ Prometheus is not responding${NC}"
    exit 1
fi

echo -e "${BLUE}→ Checking Grafana...${NC}"
if curl -s "http://localhost:3000/api/health" > /dev/null; then
    echo -e "${GREEN}✓ Grafana is healthy${NC}"
else
    echo -e "${RED}✗ Grafana is not responding${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All services are ready!${NC}"
echo ""
echo -e "${CYAN}📊 Open Grafana dashboard:${NC} ${BLUE}http://localhost:3000${NC}"
echo -e "${CYAN}   Login: admin/admin${NC}"
echo -e "${CYAN}   Navigate to: Chaos Generator Dashboard${NC}"
echo ""
echo -e "${YELLOW}Press Enter to start the demo...${NC}"
read

# Demo scenarios
activate_scenario "healthy" "Baseline performance - 50ms ± 20ms, no errors"
generate_load 20 "Testing baseline performance"

activate_scenario "latency_spike" "10% of requests get 3-second delay (p99 anomalies)"
generate_load 20 "Testing latency spikes"

activate_scenario "bimodal_latency" "90% fast (50ms), 10% slow (2s)"
generate_load 20 "Testing bimodal distribution"

activate_scenario "error_spike" "30% error rate with mixed 5xx codes"
generate_load 20 "Testing error injection"

activate_scenario "intermittent" "Random 5% failures (flaky behavior)"
generate_load 20 "Testing intermittent failures"

activate_scenario "rate_limited" "429 responses above 50 RPS"
echo -e "${BLUE}→ Generating burst traffic to trigger rate limiting...${NC}"
echo ""
for i in $(seq 1 100); do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$CHAOS_URL/api/work")
    if [ "$status" = "429" ]; then
        echo -e "  ${YELLOW}⚠${NC} Request $i: Rate limited (429)"
    elif [ "$status" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} Request $i: Success (200)"
    else
        echo -e "  ${RED}✗${NC} Request $i: Error ($status)"
    fi
done
echo ""
echo -e "${YELLOW}⏸  Pausing for 5 seconds...${NC}"
sleep 5

activate_scenario "cpu_bound" "100k hash iterations per request (CPU saturation)"
generate_load 10 "Testing CPU-bound workload"

# Reset to healthy
print_header "Demo Complete"
echo -e "${BLUE}→ Resetting to healthy baseline...${NC}"
curl -s -X POST "$CHAOS_URL/chaos/reset" | jq -r '.message'
echo ""

echo -e "${GREEN}✓ Demo completed successfully!${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Check Grafana dashboard: ${BLUE}http://localhost:3000${NC}"
echo -e "  2. Explore Prometheus: ${BLUE}http://localhost:9090${NC}"
echo -e "  3. View API docs: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  4. Run k6 tests: ${YELLOW}k6 run k6/scenarios/chaos.js${NC}"
echo ""
