# Quick Start Guide

[← Back to Index](../WIKI.md)

Get up and running with Heimr in under 5 minutes.

## Prerequisites

- **Python 3.9+**
- **pip** (Python package manager)
- **Ollama** (recommended for local AI analysis)

---

## 1. Installation

### Install Heimr

```bash
pip install heimr-ai
```

### Install Local LLM (Recommended)

Heimr works best with a local LLM for privacy-first analysis:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default model (Medium tier - best balance)
ollama pull llama3.1:8b

# Verify Ollama is running
curl http://localhost:11434
```

**Model Options:**
| Tier | Command | VRAM | Use Case |
|------|---------|------|----------|
| Small | `ollama pull llama3.2:3b` | 4 GB | CI/CD, Laptops |
| Medium | `ollama pull llama3.1:8b` | 6 GB | **Recommended** |
| Large | `ollama pull qwen2.5:14b` | 12 GB | Deep reasoning |

---

## 2. First Analysis

### Basic Usage

```bash
# Analyze a JMeter result
heimr analyze results.jtl

# Analyze k6 output
heimr analyze k6_results.json

# Analyze a HAR file (browser recording)
heimr analyze network.har
```

This generates:
- `report.md` — Detailed Markdown analysis
- `report.pdf` — PDF version for sharing

### With Observability Data

Connect to your monitoring stack for deeper correlation:

```bash
heimr analyze results.jtl \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200 \
  --output report.md
```

### Using Local Files

If you have exported observability data:

```bash
heimr analyze results.jtl \
  --prometheus ./metrics.json \
  --loki ./logs.json \
  --tempo ./traces.json
```

---

## 3. Configuration File

For repeated use, create a config file:

```bash
# Generate template
heimr config-init

# Edit with your settings
vim heimr.yaml

# Use it
heimr analyze results.jtl --config heimr.yaml
```

See [Configuration](04-configuration.md) for full reference.

---

## 4. Using Cloud LLMs (Optional)

If you prefer cloud models over local:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
heimr analyze results.jtl --llm-model gpt-4o

# Anthropic
export ANTHROPIC_API_KEY="sk-..."
heimr analyze results.jtl --llm-model claude-sonnet-4
```

---

## 5. Stats-Only Mode

For fast runs without AI analysis:

```bash
heimr analyze results.jtl --no-llm
```

This skips the LLM step and generates a pure statistical report.

---

## Next Steps

- [CLI Reference](03-cli-reference.md) — Full command documentation
- [AI Analysis Engine](05-ai-analysis-engine.md) — How the AI works
- [CI/CD Integration](08-ci-cd-integration.md) — Automate in your pipeline
- [Troubleshooting](10-troubleshooting.md) — Common issues and fixes
