#!/bin/bash
set -e

echo "Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama API..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done

# Model is baked in, but we can try to pull if missing (fallback)
# echo "Pulling Model: ${LLM_MODEL:-qwen3.5:27b}..."
# ollama pull ${LLM_MODEL:-qwen3.5:27b}

echo "Starting Heimr Cloud API on port ${PORT:-8000}..."
uvicorn heimr.web:app --host 0.0.0.0 --port ${PORT:-8000}
