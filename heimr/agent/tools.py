# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Agent tool registry — wraps existing Heimr capabilities as discrete,
schema-described tools that the ReAct loop can invoke.

Each tool is a dict with:
  - name: str
  - description: str (for the LLM)
  - parameters: dict (JSON-Schema-like, for the LLM)
  - function: callable(**kwargs) -> dict
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("heimr.agent")


# ---------------------------------------------------------------------------
# Tool result helper
# ---------------------------------------------------------------------------

def _ok(data: Any) -> Dict[str, Any]:
    """Wrap a successful tool result."""
    return {"status": "ok", "data": data}


def _error(msg: str) -> Dict[str, Any]:
    """Wrap a failed tool result."""
    return {"status": "error", "error": msg}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _parse_load_test(file_path: str, **kwargs) -> Dict[str, Any]:
    """Parse load test results, return KPIs and basic stats."""
    from heimr.analyzer import Analyzer

    try:
        file_format = Analyzer.detect_file_format(file_path)
        analyzer = Analyzer(file_path, no_llm=True)
        parser = analyzer._get_parser(file_format)
        df = parser.parse()

        if df.empty:
            return _error(f"Parsed file {file_path} but got empty DataFrame")

        # Return serializable summary instead of full DataFrame
        return _ok({
            "file": file_path,
            "format": file_format,
            "total_rows": len(df),
            "columns": list(df.columns),
            "time_range": {
                "start": str(df["timestamp_dt"].min()) if "timestamp_dt" in df.columns else None,
                "end": str(df["timestamp_dt"].max()) if "timestamp_dt" in df.columns else None,
            },
            "endpoints": list(df["endpoint"].unique()) if "endpoint" in df.columns else [],
        })
    except Exception as e:
        return _error(f"Failed to parse {file_path}: {e}")


def _compute_kpis(file_path: str, **kwargs) -> Dict[str, Any]:
    """Compute KPIs from a load test results file."""
    from heimr.analyzer import Analyzer
    from heimr.kpi import KPIEngine

    try:
        file_format = Analyzer.detect_file_format(file_path)
        analyzer = Analyzer(file_path, no_llm=True)
        parser = analyzer._get_parser(file_format)
        df = parser.parse()

        kpi_engine = KPIEngine(df)
        kpi_data = kpi_engine.get_kpi_dict()

        return _ok(kpi_data)
    except Exception as e:
        return _error(f"Failed to compute KPIs: {e}")


def _detect_anomalies(file_path: str, detector_mode: str = "simple", **kwargs) -> Dict[str, Any]:
    """Run anomaly detection on load test results."""
    from heimr.analyzer import Analyzer
    from heimr.detector import AnomalyDetector

    try:
        file_format = Analyzer.detect_file_format(file_path)
        analyzer = Analyzer(file_path, no_llm=True)
        parser = analyzer._get_parser(file_format)
        df = parser.parse()

        detector = AnomalyDetector(df, mode=detector_mode)
        anomalies = detector.detect_latency_anomalies()
        summary = detector.get_anomaly_summary(anomalies)
        per_endpoint = detector.detect_per_endpoint_anomalies()

        return _ok({
            "summary": summary,
            "per_endpoint_count": len(per_endpoint),
            "per_endpoint": {
                name: {
                    "count": data.get("count", 0),
                    "avg_latency": data.get("avg_latency", 0),
                }
                for name, data in list(per_endpoint.items())[:10]
            },
        })
    except Exception as e:
        return _error(f"Anomaly detection failed: {e}")


def _query_prometheus(
    source: str,
    start_time: str = None,
    end_time: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """Fetch system metrics from Prometheus (URL or file)."""
    from heimr.analyzer import Analyzer
    from heimr.prometheus import PrometheusClient

    try:
        url, path = Analyzer.parse_url_or_file(source)
        client = PrometheusClient(url=url or "http://localhost:9090", file_path=path)

        # Use provided times or defaults
        from datetime import datetime

        if start_time:
            st = pd.Timestamp(start_time)
        else:
            st = pd.Timestamp.now() - pd.Timedelta(hours=1)

        if end_time:
            et = pd.Timestamp(end_time)
        else:
            et = pd.Timestamp.now()

        metrics = client.get_system_metrics(st, et)

        # Summarize instead of dumping raw data
        summary = {}
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, list) and metric_data:
                values = []
                for series in metric_data:
                    for v in series.get("values", []):
                        try:
                            values.append(float(v[1]))
                        except (ValueError, IndexError):
                            pass
                if values:
                    summary[metric_name] = {
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "points": len(values),
                    }

        return _ok({"metrics": summary, "raw_metric_count": len(metrics)})
    except Exception as e:
        return _error(f"Prometheus query failed: {e}")


def _query_loki(
    source: str,
    start_time: str = None,
    end_time: str = None,
    **kwargs,
) -> Dict[str, Any]:
    """Fetch error logs from Loki (URL or file)."""
    from heimr.analyzer import Analyzer
    from heimr.loki import LokiClient

    try:
        url, path = Analyzer.parse_url_or_file(source)
        client = LokiClient(url=url or "http://localhost:3100", file_path=path)

        from datetime import datetime

        st = pd.Timestamp(start_time) if start_time else pd.Timestamp.now() - pd.Timedelta(hours=1)
        et = pd.Timestamp(end_time) if end_time else pd.Timestamp.now()

        logs = client.get_error_logs(st, et)

        # Categorize
        error_count = sum(1 for l in logs if "error" in str(l).lower())
        warn_count = sum(1 for l in logs if "warn" in str(l).lower())

        return _ok({
            "total_logs": len(logs),
            "error_count": error_count,
            "warn_count": warn_count,
            "sample_logs": [str(l)[:200] for l in logs[:5]],
        })
    except Exception as e:
        return _error(f"Loki query failed: {e}")


def _query_tempo(
    source: str,
    start_time: str = None,
    end_time: str = None,
    min_duration_ms: int = 1000,
    **kwargs,
) -> Dict[str, Any]:
    """Fetch slow traces from Tempo (URL or file)."""
    from heimr.analyzer import Analyzer
    from heimr.tempo import TempoClient

    try:
        url, path = Analyzer.parse_url_or_file(source)
        client = TempoClient(url=url or "http://localhost:3200", file_path=path)

        st = pd.Timestamp(start_time) if start_time else pd.Timestamp.now() - pd.Timedelta(hours=1)
        et = pd.Timestamp(end_time) if end_time else pd.Timestamp.now()

        traces = client.get_slow_traces(st, et, min_duration_ms=min_duration_ms)

        return _ok({
            "total_traces": len(traces),
            "sample_trace_ids": [t.get("traceID", "")[:16] for t in traces[:5]],
        })
    except Exception as e:
        return _error(f"Tempo query failed: {e}")


def _evaluate_gate(
    file_path: str,
    fail_conditions: list = None,
    gate_policy: str = "strict",
    config: dict = None,
    **kwargs,
) -> Dict[str, Any]:
    """Run full analysis and evaluate deployment gate."""
    from heimr.analyzer import Analyzer
    from heimr.agent.gate import evaluate_gate

    try:
        analyzer = Analyzer(
            file_path,
            config=config or {},
            no_llm=True,
        )
        result = analyzer.analyze()
        decision = evaluate_gate(result, fail_conditions, gate_policy)

        return _ok(decision.to_dict())
    except Exception as e:
        return _error(f"Gate evaluation failed: {e}")


def _run_full_analysis(
    file_path: str,
    config: dict = None,
    llm_url: str = None,
    llm_model: str = None,
    no_llm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Run the complete Heimr analysis pipeline (parse + KPIs + anomalies + observability + LLM)."""
    from heimr.analyzer import Analyzer

    try:
        cfg = config or {}
        analyzer = Analyzer(
            file_path,
            config=cfg,
            llm_url=llm_url,
            llm_model=llm_model,
            no_llm=no_llm,
        )
        result = analyzer.analyze()

        return _ok({
            "status": result.status,
            "kpi": result.kpi,
            "stats": {k: v for k, v in result.stats.items() if k != "per_endpoint_kpi"},
            "anomaly_summary": result.anomaly_summary,
            "failure_signals": result.failure_signals,
            "has_llm_explanation": result.llm_explanation is not None,
            "llm_error": result.llm_error,
            "prom_metrics_count": len(result.prom_metrics),
            "loki_logs_count": len(result.loki_logs),
            "tempo_traces_count": len(result.tempo_traces),
        })
    except Exception as e:
        return _error(f"Full analysis failed: {e}")


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "parse_load_test",
        "description": (
            "Parse a load test results file (k6 JSON, JMeter JTL, Gatling log, "
            "Locust CSV, or HAR). Returns metadata: row count, columns, time range, "
            "and endpoints found."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the load test results file.",
                },
            },
            "required": ["file_path"],
        },
        "function": _parse_load_test,
    },
    {
        "name": "compute_kpis",
        "description": (
            "Compute key performance indicators from load test results: "
            "throughput, latency percentiles (p50/p95/p99), error rate, "
            "concurrency, and per-endpoint breakdowns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the load test results file.",
                },
            },
            "required": ["file_path"],
        },
        "function": _compute_kpis,
    },
    {
        "name": "detect_anomalies",
        "description": (
            "Run statistical anomaly detection on load test results. "
            "Detects latency spikes and per-endpoint anomalies. "
            "Modes: 'simple' (z-score), 'mad' (robust), 'trend' (tail degradation)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the load test results file.",
                },
                "detector_mode": {
                    "type": "string",
                    "enum": ["simple", "mad", "trend"],
                    "description": "Anomaly detection algorithm. Default: 'simple'.",
                },
            },
            "required": ["file_path"],
        },
        "function": _detect_anomalies,
    },
    {
        "name": "query_prometheus",
        "description": (
            "Fetch system metrics (CPU, memory, disk, network) from Prometheus "
            "or a JSON file. Returns summary statistics per metric."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Prometheus URL (http://...) or path to JSON file.",
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO timestamp for query start.",
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO timestamp for query end.",
                },
            },
            "required": ["source"],
        },
        "function": _query_prometheus,
    },
    {
        "name": "query_loki",
        "description": (
            "Fetch error/warning logs from Loki or a JSON file. "
            "Returns log counts by level and sample messages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Loki URL (http://...) or path to JSON file.",
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO timestamp for query start.",
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO timestamp for query end.",
                },
            },
            "required": ["source"],
        },
        "function": _query_loki,
    },
    {
        "name": "query_tempo",
        "description": (
            "Fetch slow distributed traces from Tempo or a JSON file. "
            "Returns trace IDs exceeding the duration threshold."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Tempo URL (http://...) or path to JSON file.",
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO timestamp for query start.",
                },
                "end_time": {
                    "type": "string",
                    "description": "ISO timestamp for query end.",
                },
                "min_duration_ms": {
                    "type": "integer",
                    "description": "Minimum span duration to consider slow (ms). Default: 1000.",
                },
            },
            "required": ["source"],
        },
        "function": _query_tempo,
    },
    {
        "name": "evaluate_gate",
        "description": (
            "Run full analysis and evaluate a deployment gate. "
            "Returns a verdict (APPROVE/REJECT/WARN), reasons, and recommendations. "
            "Use this as the final step to decide whether to deploy."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the load test results file.",
                },
                "fail_conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of conditions, e.g. ['p99_latency > 500', 'error_rate > 1'].",
                },
                "gate_policy": {
                    "type": "string",
                    "enum": ["strict", "advisory"],
                    "description": "'strict' fails the pipeline; 'advisory' only warns.",
                },
            },
            "required": ["file_path"],
        },
        "function": _evaluate_gate,
    },
    {
        "name": "run_full_analysis",
        "description": (
            "Run the complete Heimr analysis pipeline: parse results, compute KPIs, "
            "detect anomalies, query observability sources, and optionally generate "
            "AI-powered root cause analysis. Use this for a comprehensive one-shot analysis."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the load test results file.",
                },
                "no_llm": {
                    "type": "boolean",
                    "description": "If true, skip AI analysis (statistical only). Default: false.",
                },
            },
            "required": ["file_path"],
        },
        "function": _run_full_analysis,
    },
]


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Look up a tool by name. Returns None if not found."""
    for tool in TOOL_REGISTRY:
        if tool["name"] == name:
            return tool
    return None


def get_tools_description() -> str:
    """
    Format all tools as a text block for inclusion in the LLM system prompt.
    """
    lines = []
    for tool in TOOL_REGISTRY:
        params = tool["parameters"].get("properties", {})
        required = tool["parameters"].get("required", [])

        param_lines = []
        for pname, pdef in params.items():
            req_marker = " (required)" if pname in required else ""
            param_lines.append(
                f"    - {pname}: {pdef.get('type', 'any')}{req_marker} — {pdef.get('description', '')}"
            )

        lines.append(f"## {tool['name']}")
        lines.append(f"{tool['description']}")
        if param_lines:
            lines.append("  Parameters:")
            lines.extend(param_lines)
        lines.append("")

    return "\n".join(lines)


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with the given arguments.
    Returns the tool's result dict.
    """
    tool = get_tool_by_name(name)
    if not tool:
        return _error(f"Unknown tool: {name}")

    fn = tool["function"]
    try:
        return fn(**arguments)
    except TypeError as e:
        return _error(f"Invalid arguments for {name}: {e}")
    except Exception as e:
        return _error(f"Tool {name} failed: {e}")
