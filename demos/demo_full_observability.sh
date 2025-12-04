#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

# =============================================================================
# Demo: Full Observability Analysis with Local LLM
# =============================================================================
# This demo showcases Heimr's complete feature set:
# - Local LLM analysis (Ollama with Llama 3.1)
# - Prometheus metrics correlation
# - Loki logs analysis
# - Tempo traces investigation
# - Markdown report generation
#
# Prerequisites:
# 1. Ollama installed and running (https://ollama.com/)
# 2. Llama 3.1 model pulled (`ollama pull llama3.1:8b`)
# 3. Heimr installed (`pip install .[openai]`)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
                                                
  Full Observability Demo with Local LLM
EOF
echo -e "${NC}"
echo ""

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📋 Step 1: Checking Prerequisites${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
    
    # Check if llama3.1 is available
    if curl -s http://localhost:11434/api/tags | grep -q "llama3"; then
        echo -e "${GREEN}✅ Llama 3.1 model detected${NC}"
    else
        echo -e "${YELLOW}⚠️  Llama 3.1 not found. Run: ollama pull llama3.1:8b${NC}"
    fi
else
    echo -e "${RED}❌ Ollama is not running at http://localhost:11434${NC}"
    echo -e "${YELLOW}   Please start Ollama first: ollama serve${NC}"
    echo ""
fi

# Determine heimr command
HEIMR_CMD="heimr"
if [ -f "$PROJECT_ROOT/.venv/bin/heimr" ]; then
    HEIMR_CMD="$PROJECT_ROOT/.venv/bin/heimr"
    echo -e "${GREEN}✅ Using virtual environment heimr${NC}"
elif command -v heimr &> /dev/null; then
    echo -e "${GREEN}✅ Using system heimr${NC}"
else
    echo -e "${YELLOW}⚠️  heimr not found in PATH. Using python -m heimr.cli${NC}"
    HEIMR_CMD="python -m heimr.cli"
fi

echo ""

# =============================================================================
# Step 2: Select Scenario
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📂 Step 2: Selecting Demo Scenario${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Use a scenario with interesting failures
SCENARIO="DB-001"
SCENARIO_PATH="$PROJECT_ROOT/data/mocks/$SCENARIO"

if [ ! -d "$SCENARIO_PATH" ]; then
    echo -e "${RED}❌ Demo data not found at $SCENARIO_PATH${NC}"
    echo -e "${YELLOW}   Run: python scripts/generate_mock_data.py${NC}"
    exit 1
fi

echo -e "Using scenario: ${CYAN}${BOLD}$SCENARIO${NC} (Database Slow Query)"
echo ""
echo -e "${BOLD}Available files:${NC}"
ls -la "$SCENARIO_PATH" | grep -E "\.(csv|json|log)$" | awk '{print "  📄 " $NF}'
echo ""

# =============================================================================
# Step 3: Define Input/Output Paths
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📁 Step 3: Configuring Paths${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Input files
LOAD_TEST_FILE="$SCENARIO_PATH/jmeter_results.csv"
PROMETHEUS_FILE="$SCENARIO_PATH/prometheus_metrics.json"
LOKI_FILE="$SCENARIO_PATH/loki_logs.json"
TEMPO_FILE="$SCENARIO_PATH/tempo_traces.json"

# Output file
OUTPUT_DIR="$PROJECT_ROOT/demos/output"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/demo_report_$(date +%Y%m%d_%H%M%S).md"

echo -e "  ${BOLD}Load Test:${NC}   $LOAD_TEST_FILE"
echo -e "  ${BOLD}Prometheus:${NC}  $PROMETHEUS_FILE"
echo -e "  ${BOLD}Loki Logs:${NC}   $LOKI_FILE"
echo -e "  ${BOLD}Tempo Traces:${NC} $TEMPO_FILE"
echo ""
echo -e "  ${BOLD}Output Report:${NC} ${GREEN}$OUTPUT_FILE${NC}"
echo ""

# =============================================================================
# Step 4: Display Command
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🚀 Step 4: Heimr Command${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}The following command will be executed:${NC}"
echo ""
echo -e "${CYAN}${BOLD}$HEIMR_CMD analyze \"$LOAD_TEST_FILE\" \\${NC}"
echo -e "${CYAN}${BOLD}    --explain \\${NC}"
echo -e "${CYAN}${BOLD}    --prometheus-file \"$PROMETHEUS_FILE\" \\${NC}"
echo -e "${CYAN}${BOLD}    --loki-file \"$LOKI_FILE\" \\${NC}"
echo -e "${CYAN}${BOLD}    --tempo-file \"$TEMPO_FILE\" \\${NC}"
echo -e "${CYAN}${BOLD}    --llm-url http://localhost:11434/v1 \\${NC}"
echo -e "${CYAN}${BOLD}    --llm-model llama3.1:8b \\${NC}"
echo -e "${CYAN}${BOLD}    --output \"$OUTPUT_FILE\"${NC}"
echo ""

# =============================================================================
# Step 5: Wait for User Input
# =============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}Press ENTER to execute the command, or Ctrl+C to cancel...${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
read -r

# =============================================================================
# Step 6: Execute Heimr
# =============================================================================
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}⚡ Step 6: Running Analysis${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

$HEIMR_CMD analyze "$LOAD_TEST_FILE" \
    --explain \
    --prometheus-file "$PROMETHEUS_FILE" \
    --loki-file "$LOKI_FILE" \
    --tempo-file "$TEMPO_FILE" \
    --llm-url http://localhost:11434/v1 \
    --llm-model llama3.1:8b \
    --output "$OUTPUT_FILE"

# =============================================================================
# Step 7: Summary
# =============================================================================
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✅ Demo Complete!${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Report saved to:${NC} ${GREEN}$OUTPUT_FILE${NC}"
echo ""
echo -e "  ${BOLD}View the report:${NC}"
echo -e "    cat \"$OUTPUT_FILE\""
echo ""
echo -e "  ${BOLD}Or open in your editor:${NC}"
echo -e "    code \"$OUTPUT_FILE\""
echo ""
