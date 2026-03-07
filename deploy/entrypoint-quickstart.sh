#!/bin/bash
# Entrypoint for the Heimr quickstart container.
# Waits for Ollama, then runs the agent or analyze command on the results file.
set -e

RESULTS_FILE="${RESULTS_FILE:-/data/results.json}"
HEIMR_CMD="${HEIMR_CMD:-agent}"
GATE_POLICY="${GATE_POLICY:-advisory}"
LLM_URL="${LLM_URL:-http://ollama:11434/v1}"

echo "============================================"
echo "  Heimr Performance Engineering Agent"
echo "============================================"
echo ""

# Wait for the results file (k6 may still be running)
echo "Waiting for results file: ${RESULTS_FILE} ..."
TIMEOUT=180
ELAPSED=0
while [ ! -s "$RESULTS_FILE" ]; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "ERROR: Results file not found after ${TIMEOUT}s."
        echo "Falling back to sample data..."
        RESULTS_FILE="/app/load-tests/results/demo_k6.json"
        break
    fi
done

# Give k6 a moment to finish flushing
sleep 3

echo "Analyzing: ${RESULTS_FILE}"
echo ""

if [ "$HEIMR_CMD" = "agent" ]; then
    # Wait for Ollama to be ready
    echo "Waiting for Ollama at ${LLM_URL} ..."
    ELAPSED=0
    OLLAMA_BASE="${LLM_URL%/v1}"
    until curl -sf "${OLLAMA_BASE}/api/tags" > /dev/null 2>&1; do
        sleep 2
        ELAPSED=$((ELAPSED + 2))
        if [ $ELAPSED -ge $TIMEOUT ]; then
            echo "WARNING: Ollama not ready after ${TIMEOUT}s."
            echo "Running without LLM (--no-llm)..."
            exec heimr analyze "$RESULTS_FILE" --no-llm
        fi
    done
    echo "Ollama ready."
    echo ""
    exec heimr agent "$RESULTS_FILE" \
        --gate-policy "$GATE_POLICY" \
        --verbose \
        --llm-url "$LLM_URL" \
        ${LLM_MODEL:+--llm-model "$LLM_MODEL"}
else
    exec heimr analyze "$RESULTS_FILE" --no-llm
fi
