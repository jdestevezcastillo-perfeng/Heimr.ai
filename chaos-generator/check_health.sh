#!/bin/bash

# Observability Stack Health Check

echo "🔍 Checking Observability Stack Health..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✅ $name${NC} - Ready (HTTP $response)"
        return 0
    else
        echo -e "${RED}❌ $name${NC} - Not ready (HTTP $response)"
        return 1
    fi
}

# Check each service
echo "=== Core Services ==="
check_service "Chaos Generator" "http://localhost:8000/health" "200"
check_service "Prometheus" "http://localhost:9090/-/healthy" "200"
check_service "Grafana" "http://localhost:3000/api/health" "200"

echo ""
echo "=== Observability Services ==="
check_service "Loki" "http://localhost:3100/ready" "200"
check_service "Tempo" "http://localhost:3200/ready" "200"
check_service "DCGM Exporter" "http://localhost:9400/metrics" "200"

echo ""
echo "=== API Endpoints ==="

# Test Loki API
loki_labels=$(curl -s http://localhost:3100/loki/api/v1/labels 2>/dev/null | jq -r '.status' 2>/dev/null)
if [ "$loki_labels" = "success" ]; then
    echo -e "${GREEN}✅ Loki API${NC} - Responding"
else
    echo -e "${RED}❌ Loki API${NC} - Not responding"
fi

# Test Tempo API
tempo_search=$(curl -s http://localhost:3200/api/search 2>/dev/null | jq -r '.metrics.totalJobs' 2>/dev/null)
if [ -n "$tempo_search" ]; then
    echo -e "${GREEN}✅ Tempo API${NC} - Responding"
else
    echo -e "${RED}❌ Tempo API${NC} - Not responding"
fi

# Test Prometheus API
prom_query=$(curl -s 'http://localhost:9090/api/v1/query?query=up' 2>/dev/null | jq -r '.status' 2>/dev/null)
if [ "$prom_query" = "success" ]; then
    echo -e "${GREEN}✅ Prometheus API${NC} - Responding"
else
    echo -e "${RED}❌ Prometheus API${NC} - Not responding"
fi

echo ""
echo "=== Prometheus Targets ==="
targets=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"' 2>/dev/null)
if [ -n "$targets" ]; then
    echo "$targets" | while read line; do
        if [[ $line == *"up"* ]]; then
            echo -e "${GREEN}✅${NC} $line"
        else
            echo -e "${RED}❌${NC} $line"
        fi
    done
else
    echo -e "${RED}❌ Could not fetch targets${NC}"
fi

echo ""
echo "=== Summary ==="
echo "Access URLs:"
echo "  • Grafana: http://localhost:3000 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Loki: http://localhost:3100"
echo "  • Tempo: http://localhost:3200"
echo "  • Chaos API: http://localhost:8000"
echo "  • DCGM Exporter: http://localhost:9400/metrics"
echo ""
echo "Grafana Explore:"
echo "  • Metrics: http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22Prometheus%22%7D"
echo "  • Logs: http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22Loki%22%7D"
echo "  • Traces: http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22Tempo%22%7D"
