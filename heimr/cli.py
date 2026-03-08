# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import argparse
import sys
from heimr.analyzer import AnalysisResult
from heimr.setup_llm import setup_llm

# Extracted helpers (P2.3 refactor). Kept re-exported here for compatibility.
from heimr.commands.config import load_config as _load_config_mod, normalize_config as _normalize_config_mod, merge_config_with_args as _merge_config_mod
from heimr.reporting.markdown import (
    enhance_llm_output as _enhance_llm_output_mod,
    create_correlation_chart as _create_correlation_chart_mod,
    detect_timeline_mismatch as _detect_timeline_mismatch_mod,
    extract_llm_tldr as _extract_llm_tldr_mod,
    generate_markdown_report_content as _generate_markdown_report_content_mod,
)


load_config = _load_config_mod
normalize_config = _normalize_config_mod
merge_config_with_args = _merge_config_mod


def print_banner():
    banner = """
 █████   █████           ███                           
░░███   ░░███           ░░░                            
 ░███    ░███   ██████  ████  █████████████   ████████ 
 ░███████████  ███░░███░░███ ░░███░░███░░███ ░░███░░███
 ░███░░░░░███ ░███████  ░███  ░███ ░███ ░███  ░███ ░░░ 
 ░███    ░███ ░███░░░   ░███  ░███ ░███ ░███  ░███     
 █████   █████░░██████  █████ █████░███ █████ █████    
░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░░░ ░░░ ░░░░░ ░░░░░     
"""
    print(f"\\033[1;36m{banner}\\033[0m")  # Cyan


def print_result_summary(result: AnalysisResult):
    """Prints the Level 1 and Level 2 summaries to console."""
    kpi_data = result.kpi
    anomaly_summary = result.anomaly_summary
    stats = result.stats
    
    print("\n" + "=" * 50)
    print("HEIMR REPORT (Level 1)")
    print("=" * 50)
    print(f"{'Metric':<25} | {'Value':<15}")
    print("-" * 43)
    # Status
    status_text = result.status
    print(f"{'Result':<25} | {status_text}")
    print(f"{'Duration':<25} | {kpi_data['duration']:.2f} s")
    print(f"{'Requests':<25} | {kpi_data['throughput']['total_requests']:,}")
    print(f"{'Throughput':<25} | {kpi_data['throughput']['requests_per_second']:.2f} req/s")
    print(f"{'Error Rate':<25} | {kpi_data['errors']['rate']:.2f}%")

    print(f"{'Latency P50':<25} | {kpi_data['latency']['p50']:.2f} ms")
    print(f"{'Latency P95':<25} | {kpi_data['latency']['p95']:.2f} ms")
    print(f"{'Latency P99':<25} | {kpi_data['latency']['p99']:.2f} ms")
    print("-" * 43)

    # --- REPORT SPECIFICATION: LEVEL 2 (Summary) ---
    print("\n--- Summary (Level 2) ---")
    print(f"Concurrency: Max {kpi_data['concurrency']['max']} VUs, Avg {kpi_data['concurrency']['avg']} VUs")

    # Anomaly details
    print(f"Anomalies: {anomaly_summary['count']} detected")
    if anomaly_summary['count'] > 0:
        print(f"  Avg Anomaly Latency: {anomaly_summary['avg_latency']:.2f} ms")
        
    # Observability Summaries
    if result.prom_metrics:
        print(f"Prometheus: Fetched {len(result.prom_metrics)} metric types.")
    if result.loki_logs:
        print(f"Loki: Fetched {len(result.loki_logs)} error logs.")
    if result.tempo_traces:
        print(f"Tempo: Fetched {len(result.tempo_traces)} slow traces.")

    # Overall Status reasons
    failed = result.status == "FAILED"
    status_icon = "❌" if failed else "✅"
    
    print("\n--- Overall Status ---")
    print(f"# {status_icon} {result.status}")
    if failed:
        print(f"**Reasons**: {', '.join(result.failure_signals)}")
    else:
        print("No errors or anomalies detected.")


enhance_llm_output = _enhance_llm_output_mod
create_correlation_chart = _create_correlation_chart_mod
detect_timeline_mismatch = _detect_timeline_mismatch_mod
extract_llm_tldr = _extract_llm_tldr_mod
generate_markdown_report_content = _generate_markdown_report_content_mod


def main():
    parser = argparse.ArgumentParser(
        description="Heimr.ai - AI-Powered Load Test Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Config-init command
    config_parser = subparsers.add_parser(
        "config-init",
        help="Generate an example heimr.yaml config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    config_parser.add_argument("--output", "-o", default="heimr.yaml",
                               help="Output path for the config file (default: heimr.yaml)")

    # Setup-LLM command
    setup_parser = subparsers.add_parser(
        "setup-llm",
        help="Setup Ollama and Llama 3.1 for AI analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    setup_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (auto-install)")

    # Agent command
    agent_parser = subparsers.add_parser(
        "agent",
        help="Run Heimr as an autonomous performance engineering agent.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35, width=120)
    )
    agent_parser.add_argument("file", help="Path to the load test result file")
    agent_parser.add_argument("--config", "-c", metavar="FILE", help="Path to YAML config file.")
    agent_parser.add_argument("--mode", default="autonomous",
                              choices=["autonomous", "supervised"],
                              help="Agent mode (default: autonomous)")
    agent_parser.add_argument("--gate-policy", default="strict",
                              choices=["strict", "advisory"],
                              help="Gate policy: strict fails pipeline, advisory only warns (default: strict)")
    agent_parser.add_argument("--max-iterations", type=int, default=10,
                              help="Max ReAct loop iterations (default: 10)")
    agent_parser.add_argument("--prometheus", help="Prometheus server URL or path to JSON file")
    agent_parser.add_argument("--loki", help="Loki server URL or path to JSON file")
    agent_parser.add_argument("--tempo", help="Tempo server URL or path to JSON file")
    agent_parser.add_argument("--llm-url", default=None, help="Base URL for LLM API")
    agent_parser.add_argument("--llm-model", default=None, help="LLM model to use")
    agent_parser.add_argument("--fail-condition", action="append", help="Fail if condition is met")
    agent_parser.add_argument("--ci-summary", nargs="?", const="GITHUB_STEP_SUMMARY",
                              help="Generate GitHub Actions Step Summary")
    agent_parser.add_argument("--junit-output", help="Path to save JUnit XML report")
    agent_parser.add_argument("--verbose", "-v", action="store_true", help="Print agent reasoning steps")
    agent_parser.add_argument("--log-level", default=None, help="Log level (DEBUG, INFO, WARNING, ERROR)")
    agent_parser.add_argument("--task", default=None,
                              help="Custom task description (default: auto-generated from config)")

    # MCP command
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Start the Heimr MCP (Model Context Protocol) server.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35, width=120)
    )
    mcp_parser.add_argument("--transport", choices=["stdio", "streamable-http"],
                            default="stdio",
                            help="MCP transport (default: stdio)")
    mcp_parser.add_argument("--port", type=int, default=8000,
                            help="Port for HTTP transport (default: 8000)")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a load test result file and detect anomalies.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35, width=120)
    )
    analyze_parser.add_argument("file", help="Path to the load test result file (supports .jtl, .json, .log, .csv)")
    analyze_parser.add_argument("--config", "-c", metavar="FILE", help="Path to YAML config file.")
    analyze_parser.add_argument("--output", help="Path to save the generated analysis report (Markdown format)")
    analyze_parser.add_argument("--no-llm", action="store_true", help="Disable AI-powered analysis")
    analyze_parser.add_argument("--explain", action="store_true",
                                help="(Deprecated) AI analysis is on by default. Use --no-llm to disable.")
    analyze_parser.add_argument("--prometheus", help="Prometheus server URL or path to JSON file")
    analyze_parser.add_argument("--loki", help="Loki server URL or path to JSON file")
    analyze_parser.add_argument("--tempo", help="Tempo server URL or path to JSON file")
    analyze_parser.add_argument("--llm-url", default=None, help="Base URL for LLM API")
    analyze_parser.add_argument("--llm-model", default=None, help="LLM model to use")
    analyze_parser.add_argument("--prompt-template", help="Path to custom LLM prompt template file")
    analyze_parser.add_argument("--llm-timeout-sec", type=float, default=None, help="LLM call timeout in seconds")
    analyze_parser.add_argument("--llm-max-retries", type=int, default=None, help="Retry count for LLM calls")
    analyze_parser.add_argument("--log-level", default=None, help="Log level (DEBUG, INFO, WARNING, ERROR)")
    analyze_parser.add_argument("--grafana-url", default=None, help="Grafana base URL for dashboard links")
    analyze_parser.add_argument("--grafana-dashboard-uid", default=None, help="Grafana dashboard UID to link")
    # Comparison arguments
    analyze_parser.add_argument("--compare-baseline", help="Path to baseline load test file for comparison")
    analyze_parser.add_argument("--compare-prometheus", help="Path to baseline Prometheus metrics file")
    analyze_parser.add_argument("--compare-loki", help="Path to baseline Loki logs file")
    analyze_parser.add_argument("--compare-tempo", help="Path to baseline Tempo traces file")
    analyze_parser.add_argument("--fail-on-regression", type=float, help="Fail if metric worsens by %%")
    analyze_parser.add_argument("--fail-condition", action="append", help="Fail if condition is met")
    analyze_parser.add_argument("--tag", action="append", help="Add metadata tag to report")
    analyze_parser.add_argument("--ci-summary", nargs="?", const="GITHUB_STEP_SUMMARY", help="Generate GH Summary")
    analyze_parser.add_argument("--junit-output", help="Path to save JUnit XML report")
    analyze_parser.add_argument("--detector-mode", default=None,
                                help="Anomaly detector mode: simple (default), mad, trend")
    analyze_parser.add_argument("--trend-threshold", type=float, default=None,
                                help="Trend detector threshold (e.g., 0.5 = 50% slower tail)")
    # JVM Analysis arguments
    analyze_parser.add_argument("--jvm-thread-dump", help="Path to JVM thread dump file (jstack output)")
    analyze_parser.add_argument("--jvm-heap-dump", help="Path to JVM heap histogram file (jmap -histo output)")
    analyze_parser.add_argument("--jvm-gc-log", help="Path to JVM GC log file (-Xlog:gc* format)")

    args = parser.parse_args()

    if args.command == "config-init":
        config_content = '''# Heimr Configuration File
# Documentation: https://github.com/jdestevezcastillo-perfeng/Heimr.ai/wiki

# === Load Test Analysis ===
# AI-powered root cause analysis is enabled by default.
# Set disable_llm to true for statistical-only analysis.
disable_llm: false

# LLM Configuration
# Use local Ollama models or remote providers (OpenAI-compatible API)
llm_model: medium  # Options: small, medium, large or explicit model name
llm_url: http://localhost:11434/v1  # Default Ollama API URL

# === Observability Integrations ===
# Uncomment and set paths/URLs to enable multi-signal analysis.
# Supports local files (.json) or HTTP URLs.

# Prometheus (Metrics)
# prometheus: http://prometheus:9090
# prometheus: ./data/prometheus_metrics.json

# Loki (Logs)
# loki: http://loki:3100
# loki: ./data/loki_logs.json

# Tempo (Traces)
# tempo: http://tempo:3200
# tempo: ./data/tempo_traces.json

# === Reporting ===
# output: ./reports/analysis.html  # Default output path
# open_browser: true               # Open report automatically
'''
        with open(args.output, 'w') as f:
            f.write(config_content)
        print(f"✓ Created config file: {args.output}")
        sys.exit(0)

    elif args.command == "setup-llm":
        from heimr.setup_llm import setup_llm
        success = setup_llm(interactive=not args.non_interactive)
        sys.exit(0 if success else 1)

    elif args.command == "agent":
        from heimr.commands.agent import handle_agent
        handle_agent(args, load_config, normalize_config, print_banner)

    elif args.command == "mcp":
        try:
            from heimr.agent.mcp_server import mcp as mcp_app
        except ImportError:
            print("Error: MCP SDK not installed. Install with:", file=sys.stderr)
            print("  pip install mcp", file=sys.stderr)
            print("  # or", file=sys.stderr)
            print("  pip install heimr[mcp]", file=sys.stderr)
            sys.exit(1)

        print_banner()
        print(f"🔌 Starting Heimr MCP Server (transport: {args.transport})")
        if args.transport == "streamable-http":
            print(f"   Listening on http://localhost:{args.port}/mcp")
            mcp_app.run(transport="streamable-http", port=args.port)
        else:
            print("   Communicating via stdio")
            mcp_app.run(transport="stdio")

    elif args.command == "analyze":
        from heimr.commands.analyze import handle_analyze
        handle_analyze(args, load_config, normalize_config, merge_config_with_args,
                       print_banner, print_result_summary)

if __name__ == "__main__":
    main()
