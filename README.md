```text
 █████   █████           ███
░░███   ░░███           ░░░
 ░███    ░███   ██████  ████  █████████████   ████████
 ░███████████  ███░░███░░███ ░░███░░███░░███ ░░███░░███
 ░███░░░░░███ ░███████  ░███  ░███ ░███ ░███  ░███ ░░░
 ░███    ░███ ░███░░░   ░███  ░███ ░███ ░███  ░███
 █████   █████░░██████  █████ █████░███ █████ █████
░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░░░ ░░░ ░░░░░ ░░░░░
```

# Heimr.ai

**Autonomous performance engineering agent for CI/CD pipelines.**

Analyzes load test results, correlates observability signals, and makes deployment gate decisions — with a full audit trail for every reasoning step.

---

## How It Works

Heimr is an AI agent that uses a **ReAct loop** (Reason → Act → Observe) to autonomously analyze your load tests:

```
Parse Results → Compute KPIs → Detect Anomalies → Query Observability → Verdict
   (k6, JMeter,    (P50-P99,       (z-score, MAD,     (Prometheus,       APPROVE
    Gatling,         throughput,      trend analysis)     Loki, Tempo)       or
    Locust, HAR)     error rate)                                           REJECT
```

The agent decides which tools to call, correlates signals across sources, and produces a traceable deployment decision. Every tool call and reasoning step is saved to an audit trail.

---

## Quick Start

### Installation

```bash
pip install heimr-ai

# Add reporting dependencies for HTML/Markdown/PDF outputs
pip install heimr-ai[reports]

# Add web or MCP support only when you need it
pip install heimr-ai[web]
pip install heimr-ai[mcp]

# For local AI analysis (recommended — your data stays on your machine)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b
```

### Optional Extras

| Feature | Install |
|---|---|
| Core CLI + agent analysis | `pip install heimr-ai` |
| HTML/Markdown/PDF reports | `pip install heimr-ai[reports]` |
| Web API | `pip install heimr-ai[web]` |
| MCP server | `pip install heimr-ai[mcp]` |
| All optional features | `pip install heimr-ai[all]` |

### Agent Mode — Deployment Gating

```bash
heimr agent results.json \
  --gate-policy strict \
  --prometheus http://localhost:9090 \
  --fail-condition "p99_latency > 500" \
  --fail-condition "error_rate > 1" \
  --verbose
```

Output: `APPROVE` or `REJECT` with reasoning + JSON audit trail.

### GitHub Action

```yaml
- name: Performance Gate
  uses: jdestevezcastillo-perfeng/heimr-ai@main
  with:
    results-file: results.json
    gate-policy: strict
    fail-conditions: "p99_latency > 500, error_rate > 1"
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}  # or use local Ollama
```

### Detailed Reports

```bash
heimr analyze results.json \
  --output report.html \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200
```

Generates interactive HTML reports with Plotly charts, per-endpoint breakdowns, and AI root cause analysis.

Note: report generation requires `heimr-ai[reports]`.

### MCP Server — Claude Integration

```bash
# Add Heimr tools to Claude Code
claude mcp add heimr-perf -- python -m heimr.agent.mcp_server

# Or run as HTTP server
heimr mcp --transport streamable-http --port 8000
```

Use all 8 Heimr analysis tools directly from Claude Code, Claude Desktop, or any MCP client.

### Docker Quickstart

```bash
# Full pipeline: demo server → k6 load test → Heimr agent → verdict
docker compose -f docker-compose.quickstart.yml up
```

---

## Supported Formats

| Load Testing | Observability |
|-------------|---------------|
| k6 (JSON) | Prometheus (metrics) |
| JMeter (JTL/CSV) | Loki (logs) |
| Gatling (simulation.log) | Tempo (traces) |
| Locust (stats CSV) | Grafana (dashboard links) |
| HAR (browser recordings) | |

---

## Privacy & Security

- **Local LLM**: Qwen 3.5 via Ollama — no API calls, no data leaves your infrastructure
- **Offline**: Works without internet connectivity
- **Optional cloud**: OpenAI or Anthropic Claude for enhanced analysis when desired

---

## Documentation

**[Full Documentation](docs/WIKI.md)** — Quick Start, Deployment Gating, MCP Integration, Architecture, CI/CD, and more.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

**GNU Affero General Public License v3 (AGPL v3)**

You are free to use, modify, and distribute Heimr under AGPL v3 terms. If you run Heimr as a network service, you must make your source code available to your users.

**Commercial licensing** is available for proprietary integrations, closed-source SaaS, or redistribution without copyleft obligations. Contact [jd.estevezcastillo@gmail.com](mailto:jd.estevezcastillo@gmail.com) for terms.

| Use Case | License |
|----------|---------|
| Open source / internal use | AGPL v3 (free) |
| Educational / research | AGPL v3 (free) |
| SaaS / web service | Commercial |
| Proprietary integration | Commercial |

For the full license text, see [LICENSE](./LICENSE).
