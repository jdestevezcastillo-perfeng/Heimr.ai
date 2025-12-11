#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

# Demo: Local LLM Analysis with Heimr
# Prerequisites:
# 1. Ollama installed and running (https://ollama.com/)
# 2. Llama 3 model pulled (`ollama pull llama3`)
# 3. Heimr installed (`pip install .`)

echo "🚀 Starting Local LLM Demo..."

# Check if Ollama is running (optional check)
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "⚠️  Warning: Ollama does not seem to be running at http://localhost:11434"
    echo "   Please start Ollama to see the full effect."
else
    echo "✅ Ollama detected."
fi

echo ""
echo "📊 Analyzing sample JTL file with Llama 3.1..."
echo "   Command: heimr analyze heimr/data/sample.jtl --llm-url http://localhost:11434/v1 --llm-model llama3.1:8b"
echo ""

# Determine project root and heimr command
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HEIMR_CMD="heimr"

if [ -f "$PROJECT_ROOT/.venv/bin/heimr" ]; then
    HEIMR_CMD="$PROJECT_ROOT/.venv/bin/heimr"
    echo "✅ Using virtual environment: $HEIMR_CMD"
fi

# Run Heimr
$HEIMR_CMD analyze "$PROJECT_ROOT/heimr/data/sample.jtl" --llm-url http://localhost:11434/v1 --llm-model llama3.1:8b

echo ""
echo "✅ Demo Complete!"
