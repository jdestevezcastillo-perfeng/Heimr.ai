# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Heimr MCP (Model Context Protocol) server.

Exposes Heimr performance engineering capabilities as MCP tools that can
be consumed by any MCP-compatible client (Claude Code, Claude Desktop,
VS Code, Cursor, Windsurf, etc.).

Requires: pip install mcp (or pip install heimr[mcp])

Usage:
    # stdio transport (for Claude Desktop / Claude Code)
    python -m heimr.agent.mcp_server

    # streamable-http transport (for remote clients)
    python -m heimr.agent.mcp_server --transport streamable-http --port 8000

    # Claude Code integration:
    claude mcp add heimr-perf -- python -m heimr.agent.mcp_server

    # Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "heimr-perf": {
          "command": "python",
          "args": ["-m", "heimr.agent.mcp_server"]
        }
      }
    }
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger("heimr.mcp")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "Error: MCP SDK not installed. Install with:\n"
        "  pip install mcp\n"
        "  # or\n"
        "  pip install heimr[mcp]",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Create MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Heimr Performance Engineering",
    instructions=(
        "Heimr is a performance engineering agent. Use these tools to analyze "
        "load test results, detect anomalies, query observability data, and "
        "make deployment gate decisions. Start with parse_load_test or "
        "run_full_analysis, then drill down with specific tools."
    ),
)


# ---------------------------------------------------------------------------
# Tool implementations as MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_load_test(file_path: str) -> dict:
    """Parse a load test results file (k6 JSON, JMeter JTL, Gatling log,
    Locust CSV, or HAR). Returns metadata: row count, columns, time range,
    and endpoints found."""
    from heimr.agent.tools import execute_tool
    return execute_tool("parse_load_test", {"file_path": file_path})


@mcp.tool()
def compute_kpis(file_path: str) -> dict:
    """Compute key performance indicators from load test results: throughput,
    latency percentiles (p50/p95/p99), error rate, concurrency, and
    per-endpoint breakdowns."""
    from heimr.agent.tools import execute_tool
    return execute_tool("compute_kpis", {"file_path": file_path})


@mcp.tool()
def detect_anomalies(file_path: str, detector_mode: str = "simple") -> dict:
    """Run statistical anomaly detection on load test results. Detects latency
    spikes and per-endpoint anomalies.
    Modes: 'simple' (z-score), 'mad' (robust), 'trend' (tail degradation)."""
    from heimr.agent.tools import execute_tool
    return execute_tool("detect_anomalies", {
        "file_path": file_path,
        "detector_mode": detector_mode,
    })


@mcp.tool()
def query_prometheus(
    source: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> dict:
    """Fetch system metrics (CPU, memory, disk, network) from Prometheus
    or a JSON file. Returns summary statistics per metric."""
    from heimr.agent.tools import execute_tool
    return execute_tool("query_prometheus", {
        "source": source,
        "start_time": start_time,
        "end_time": end_time,
    })


@mcp.tool()
def query_loki(
    source: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> dict:
    """Fetch error/warning logs from Loki or a JSON file. Returns log counts
    by level and sample messages."""
    from heimr.agent.tools import execute_tool
    return execute_tool("query_loki", {
        "source": source,
        "start_time": start_time,
        "end_time": end_time,
    })


@mcp.tool()
def query_tempo(
    source: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    min_duration_ms: int = 1000,
) -> dict:
    """Fetch slow distributed traces from Tempo or a JSON file. Returns
    trace IDs exceeding the duration threshold."""
    from heimr.agent.tools import execute_tool
    return execute_tool("query_tempo", {
        "source": source,
        "start_time": start_time,
        "end_time": end_time,
        "min_duration_ms": min_duration_ms,
    })


@mcp.tool()
def evaluate_gate(
    file_path: str,
    fail_conditions: Optional[List[str]] = None,
    gate_policy: str = "strict",
) -> dict:
    """Run full analysis and evaluate a deployment gate. Returns verdict
    (APPROVE/REJECT/WARN), reasons, confidence score, and recommendations.
    Use this as the final step to decide whether to deploy."""
    from heimr.agent.tools import execute_tool
    return execute_tool("evaluate_gate", {
        "file_path": file_path,
        "fail_conditions": fail_conditions,
        "gate_policy": gate_policy,
    })


@mcp.tool()
def run_full_analysis(
    file_path: str,
    no_llm: bool = False,
) -> dict:
    """Run the complete Heimr analysis pipeline: parse results, compute KPIs,
    detect anomalies, query observability sources, and optionally generate
    AI-powered root cause analysis. Use this for a comprehensive one-shot analysis."""
    from heimr.agent.tools import execute_tool
    return execute_tool("run_full_analysis", {
        "file_path": file_path,
        "no_llm": no_llm,
    })


# ---------------------------------------------------------------------------
# MCP Resources — expose analysis context
# ---------------------------------------------------------------------------

@mcp.resource("heimr://tools")
def list_available_tools() -> str:
    """List all available Heimr performance engineering tools and their descriptions."""
    from heimr.agent.tools import get_tools_description
    return get_tools_description()


@mcp.resource("heimr://supported-formats")
def supported_formats() -> str:
    """List supported load test result file formats."""
    return """# Supported Load Test Formats

| Format | File Extension | Tool |
|--------|---------------|------|
| k6 | .json | k6 |
| JMeter | .jtl, .csv | JMeter |
| Gatling | simulation.log | Gatling |
| Locust | .csv | Locust |
| HAR | .har | Browser DevTools |

# Supported Observability Sources

| Source | Protocol | Data Type |
|--------|----------|-----------|
| Prometheus | HTTP API / JSON file | Metrics (CPU, memory, disk, network) |
| Loki | HTTP API / JSON file | Logs (errors, warnings) |
| Tempo | HTTP API / JSON file | Traces (slow spans) |
"""


# ---------------------------------------------------------------------------
# MCP Prompts — reusable analysis templates
# ---------------------------------------------------------------------------

@mcp.prompt()
def analyze_load_test(file_path: str) -> str:
    """Generate a prompt for comprehensive load test analysis."""
    return f"""Analyze the load test results at '{file_path}'.

Follow this analysis workflow:
1. First, use parse_load_test to understand the data structure
2. Use compute_kpis to get quantitative performance metrics
3. Use detect_anomalies to identify statistical outliers
4. If observability sources are available, query them for correlated signals
5. Finally, use evaluate_gate to produce a deployment decision

Provide a comprehensive report with:
- Executive summary of performance results
- Key metrics (throughput, latencies, error rates)
- Anomaly analysis with root cause hypotheses
- Deployment recommendation with confidence level
- Actionable improvement suggestions"""


@mcp.prompt()
def deployment_gate(
    file_path: str,
    fail_conditions: str = "",
    policy: str = "strict",
) -> str:
    """Generate a prompt for deployment gate evaluation."""
    conditions_text = ""
    if fail_conditions:
        conditions_text = f"\nApply these fail conditions: {fail_conditions}"

    return f"""Evaluate whether the build should be deployed based on load test results.

Results file: {file_path}
Gate policy: {policy}{conditions_text}

Use the evaluate_gate tool to get a structured verdict, then explain:
1. Whether the build should be deployed (APPROVE/REJECT/WARN)
2. Key reasons for the decision
3. Any risks identified
4. Recommended next steps"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the Heimr MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Heimr MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport type (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
