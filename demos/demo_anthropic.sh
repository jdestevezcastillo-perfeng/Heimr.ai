#!/bin/bash
# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html

# Demo: Anthropic API Analysis with Heimr
# Prerequisites:
# 1. ANTHROPIC_API_KEY environment variable set
# 2. Heimr installed (`pip install .`)

echo "🚀 Starting Anthropic API Demo..."

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY is not set."
    echo "   Please export it: export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi

echo "✅ API Key detected."

echo ""
echo "📊 Analyzing sample JTL file with Claude 3 Opus..."
echo "   Command: heimr analyze heimr/data/sample.jtl --explain"
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
# By default, if ANTHROPIC_API_KEY is set and no --llm-url is provided, it uses Anthropic.
$HEIMR_CMD analyze "$PROJECT_ROOT/heimr/data/sample.jtl" --explain

echo ""
echo "✅ Demo Complete!"
