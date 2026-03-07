# MCP Integration

[← Back to Index](../WIKI.md)

Heimr exposes all its analysis capabilities as an **MCP (Model Context Protocol) server**, making them directly available in Claude Code, Claude Desktop, VS Code, Cursor, and any MCP-compatible client.

---

## What Is MCP?

MCP is an open protocol that lets AI assistants use external tools. When you add Heimr as an MCP server, Claude can directly call Heimr's analysis tools — no CLI needed.

---

## Setup

### Claude Code

```bash
claude mcp add heimr-perf -- python -m heimr.agent.mcp_server
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "heimr-perf": {
      "command": "python",
      "args": ["-m", "heimr.agent.mcp_server"]
    }
  }
}
```

### HTTP Transport (Remote)

For shared or remote deployments:

```bash
heimr mcp --transport streamable-http --port 8000
```

Then configure your MCP client to connect to `http://localhost:8000/mcp`.

---

## Installation

MCP support requires the `mcp` extra:

```bash
pip install heimr-ai[mcp]
```

---

## Available Tools

Once connected, Claude has access to 8 analysis tools:

| Tool | Description |
|------|-------------|
| `parse_load_test` | Parse a load test file and return format, metadata, endpoints, time range |
| `compute_kpis` | Calculate throughput, latency percentiles, error rate, concurrency, per-endpoint KPIs |
| `detect_anomalies` | Run anomaly detection with configurable mode (`simple`, `mad`, `trend`) |
| `query_prometheus` | Fetch system metrics from Prometheus (URL or JSON file) |
| `query_loki` | Fetch application logs from Loki (URL or JSON file) |
| `query_tempo` | Fetch slow distributed traces from Tempo (URL or JSON file) |
| `evaluate_gate` | Run full pipeline and produce a deployment verdict (APPROVE/REJECT/WARN) |
| `run_full_analysis` | One-shot complete analysis with optional LLM root cause explanation |

## Resources

| Resource URI | Description |
|-------------|-------------|
| `heimr://tools` | Full tool descriptions and parameter schemas |
| `heimr://supported-formats` | Supported load test formats and observability sources |

## Prompts

| Prompt | Parameters | Description |
|--------|-----------|-------------|
| `analyze_load_test` | `file_path` | Generate a comprehensive analysis prompt |
| `deployment_gate` | `file_path`, `fail_conditions`, `policy` | Generate a deployment gate decision prompt |

---

## Example Conversation

Once Heimr is configured as an MCP server, you can interact with it naturally:

**You:** "Analyze the load test at /tmp/results.json and tell me if it's safe to deploy"

**Claude:** *Calls `parse_load_test` → `compute_kpis` → `detect_anomalies` → `evaluate_gate`*

"The load test shows 5,000 requests with a P99 of 320ms and 0.1% error rate. No anomalies detected. The gate evaluation returns **APPROVE** — this build is safe to deploy."

---

## Next Steps

- [Deployment Gating](02-deployment-gating.md) — Agent mode CLI usage
- [Performance Reports](04-performance-reports.md) — Generate HTML/PDF reports
- [CLI Reference](07-cli-reference.md) — All commands and flags
