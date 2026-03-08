# Quick Start Guide

[← Back to Index](../WIKI.md)

Get up and running with Heimr in under 5 minutes.

## Prerequisites

- **Python 3.9+**
- **pip** (Python package manager)
- **Ollama** (recommended for local AI analysis)

---

## 1. Installation

```bash
pip install heimr-ai

# Optional: report generation dependencies
pip install heimr-ai[reports]

# Optional: web API support
pip install heimr-ai[web]

# Install local LLM (recommended — your data stays on your machine)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b
```

**Model Options:**
| Tier | Command | VRAM | Use Case |
|------|---------|------|----------|
| Small | `ollama pull qwen3.5:4b` | 4 GB | CI/CD, Laptops |
| Medium | `ollama pull qwen3.5:9b` | 8 GB | **Recommended** |
| Large | `ollama pull qwen3.5:27b` | 20 GB | Deep reasoning |

---

## 2. Agent Mode — Deployment Gating

The primary way to use Heimr. The agent autonomously analyzes your load test and makes a deployment decision:

```bash
heimr agent results.json \
  --gate-policy strict \
  --fail-condition "p99_latency > 500" \
  --verbose
```

The agent will:
1. Parse your load test results
2. Compute KPIs (latency percentiles, throughput, error rate)
3. Detect anomalies (z-score, MAD, trend analysis)
4. Query observability sources (if configured)
5. Output a **verdict** (`APPROVE` or `REJECT`) with full reasoning

Add observability for deeper analysis:

```bash
heimr agent results.json \
  --gate-policy strict \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200 \
  --fail-condition "p99_latency > 500" \
  --verbose
```

See [Deployment Gating](02-deployment-gating.md) for the full guide.

---

## 3. GitHub Action

Drop Heimr into your CI/CD pipeline in 3 lines:

```yaml
- name: Performance Gate
  uses: jdestevezcastillo-perfeng/heimr-ai@main
  with:
    results-file: results.json
    gate-policy: strict
    fail-conditions: "p99_latency > 500, error_rate > 1"
```

See [CI/CD Integration](06-ci-cd-integration.md) for GitHub Actions, Jenkins, and GitLab CI examples.

---

## 4. Detailed Reports

Need the full story for stakeholders? Use `analyze` to generate interactive reports:

```bash
heimr analyze results.json \
  --output report.html \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200
```

Generates:
- **HTML report** — Interactive Plotly charts, per-endpoint breakdowns, AI root cause analysis
- **Markdown report** — GitHub/GitLab-friendly with static charts
- **PDF report** — Professional formatting for sharing

Install `heimr-ai[reports]` first to enable report generation.

See [Performance Reports](04-performance-reports.md) for details.

---

## 5. MCP Server — Claude Integration

Use Heimr tools directly from Claude Code or Claude Desktop:

```bash
# Add to Claude Code
claude mcp add heimr-perf -- python -m heimr.agent.mcp_server
```

See [MCP Integration](03-mcp-integration.md) for setup instructions.

---

## 6. Configuration File

For repeated use, create a config file:

```bash
heimr config-init    # Generate template
vim heimr.yaml       # Edit with your settings
heimr agent results.json --config heimr.yaml
```

See [Configuration](08-configuration.md) for full reference.

---

## 7. Cloud LLMs (Optional)

If you prefer cloud models over local:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
heimr agent results.json --llm-model gpt-4o

# Anthropic
export ANTHROPIC_API_KEY="sk-..."
heimr agent results.json --llm-model claude-sonnet-4
```

---

## Next Steps

- [Deployment Gating](02-deployment-gating.md) — Agent mode deep dive
- [MCP Integration](03-mcp-integration.md) — Claude Code/Desktop setup
- [Performance Reports](04-performance-reports.md) — Detailed HTML/PDF reports
- [CLI Reference](07-cli-reference.md) — Full command documentation
- [Troubleshooting](12-troubleshooting.md) — Common issues and fixes
