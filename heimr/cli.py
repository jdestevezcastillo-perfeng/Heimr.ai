# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import argparse
import sys
import os
import yaml
from heimr.parsers.jtl import JTLParser
from heimr.parsers.k6 import K6Parser
from heimr.parsers.gatling import GatlingParser
from heimr.parsers.locust import LocustParser
from heimr.detector import AnomalyDetector
from heimr.llm import LLMClient
from heimr.prometheus import PrometheusClient
from heimr.loki import LokiClient
from heimr.tempo import TempoClient


def load_config(config_path: str) -> dict:
    """
    Load configuration from a YAML file.
    
    Example heimr.yaml:
        prometheus_url: http://localhost:9090
        loki_url: http://localhost:3100
        tempo_url: http://localhost:3200
        llm_url: http://localhost:11434/v1
        llm_model: llama3.1:8b
        explain: true
        output: reports/analysis.md
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Convert YAML keys (snake_case) to argparse format (with underscores)
    # YAML uses snake_case, argparse dest uses underscores
    return config


def merge_config_with_args(args, config: dict):
    """
    Merge config file settings with command line arguments.
    CLI arguments take precedence over config file.
    """
    # Map config keys to argparse attribute names
    key_mapping = {
        'prometheus_url': 'prometheus_url',
        'prometheus_file': 'prometheus_file',
        'loki_url': 'loki_url',
        'loki_file': 'loki_file',
        'tempo_url': 'tempo_url',
        'tempo_file': 'tempo_file',
        'llm_url': 'llm_url',
        'llm_model': 'llm_model',
        'explain': 'explain',
        'output': 'output',
        'format': 'format',
    }
    
    for config_key, arg_key in key_mapping.items():
        if config_key in config:
            # Only set from config if CLI arg was not provided
            current_value = getattr(args, arg_key, None)
            if current_value is None or (isinstance(current_value, bool) and not current_value):
                setattr(args, arg_key, config[config_key])
    
    return args


def get_parser(filepath: str, format_arg: str = None):
    """
    Returns the appropriate parser based on file extension or argument.
    """
    if format_arg:
        if format_arg == 'jtl': return JTLParser(filepath)
        if format_arg == 'k6': return K6Parser(filepath)
        if format_arg == 'gatling': return GatlingParser(filepath)
        if format_arg == 'locust': return LocustParser(filepath)
    
    # Auto-detect
    if filepath.endswith('.jtl') or filepath.endswith('.csv'):
        # Check if it's a Locust history file
        if 'stats_history' in filepath:
            return LocustParser(filepath)
        return JTLParser(filepath)
    if filepath.endswith('.json'):
        return K6Parser(filepath)
    if filepath.endswith('.log'):
        return GatlingParser(filepath)
    
    raise ValueError("Could not detect file format. Please use --format.")

def print_banner():
    banner = """
   ▄▄▄  ▄▄▄                                    
  █▀██  ██                                     
    ██  ██         ▀▀ ▄        ▄             ▀▀
    ██████   ▄█▀█▄ ██ ███▄███▄ ████▄   ▄▀▀█▄ ██
    ██  ██   ██▄█▀ ██ ██ ██ ██ ██      ▄█▀██ ██
  ▀██▀  ▀██▄▄▀█▄▄▄▄██▄██ ██ ▀█▄█▀  ██ ▄▀█▄██▄██
"""
    print(f"\\033[1;36m{banner}\\033[0m") # Cyan

def print_status(stats, anomaly_summary):
    failed = False
    reasons = []
    
    if stats.get('error_rate', 0) > 0:
        failed = True
        reasons.append(f"Error Rate: {stats['error_rate']:.2f}%")
    
    if anomaly_summary['count'] > 0:
        failed = True
        reasons.append(f"Anomalies: {anomaly_summary['count']}")
        
    print("\\n" + "="*50)
    if failed:
        print(f"\\033[1;31m❌ FAILED\\033[0m")
        print(f"Reasons: {', '.join(reasons)}")
    else:
        print(f"\\033[1;32m✅ PASSED\\033[0m")
        print("No errors or anomalies detected.")
    print("="*50 + "\\n")

def main():
    parser = argparse.ArgumentParser(description="Heimr.ai - AI-Powered Load Test Analysis")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Config-init command
    config_parser = subparsers.add_parser("config-init", help="Generate an example heimr.yaml config file.")
    config_parser.add_argument("--output", "-o", default="heimr.yaml", help="Output path for the config file (default: heimr.yaml)")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a load test result file and detect anomalies.")
    analyze_parser.add_argument("file", help="Path to the load test result file (supports .jtl, .json, .log, .csv)")
    analyze_parser.add_argument("--config", "-c", metavar="FILE", help="""Path to YAML config file. Available keys:
  prometheus_url, prometheus_file, loki_url, loki_file,
  tempo_url, tempo_file, llm_url, llm_model, explain,
  output, format. Run 'heimr config-init' to generate a template.""")
    analyze_parser.add_argument("--format", choices=['jtl', 'k6', 'gatling', 'locust'], help="Explicitly specify the file format (auto-detected by default)")
    analyze_parser.add_argument("--output", help="Path to save the generated analysis report (Markdown format)")
    analyze_parser.add_argument("--dashboard", help="Path to save the generated HTML dashboard")
    analyze_parser.add_argument("--explain", action="store_true", help="Enable AI-powered Root Cause Analysis (requires API key or local LLM)")
    analyze_parser.add_argument("--prometheus-url", help="URL of the Prometheus server to fetch system metrics (e.g., http://localhost:9090)")
    analyze_parser.add_argument("--prometheus-file", help="Path to a local JSON file containing Prometheus metrics")
    analyze_parser.add_argument("--loki-url", help="URL of the Loki server to fetch logs (e.g., http://localhost:3100)")
    analyze_parser.add_argument("--loki-file", help="Path to a local JSON file containing Loki logs")
    analyze_parser.add_argument("--tempo-url", help="URL of the Tempo server to fetch traces (e.g., http://localhost:3200)")
    analyze_parser.add_argument("--tempo-file", help="Path to a local JSON file containing Tempo traces")
    analyze_parser.add_argument("--llm-url", help="Base URL for a local LLM API (e.g., http://localhost:11434/v1 for Ollama)")
    analyze_parser.add_argument("--llm-model", help="Name of the LLM model to use (e.g., gpt-5.1, claude-sonnet-4-5-20250514, llama3)")

    args = parser.parse_args()

    if args.command == "config-init":
        # Generate example config file
        config_content = '''# Heimr Configuration File
# Generated by: heimr config-init
# Documentation: https://github.com/jdestevezcastillo-perfeng/Heimr.ai

# ============================================================================
# Observability Sources
# ============================================================================

# Prometheus - for system metrics (CPU, memory, latency histograms)
prometheus_url: http://localhost:9090
# prometheus_file: ./data/prometheus_metrics.json  # Use local file instead

# Loki - for log aggregation
loki_url: http://localhost:3100
# loki_file: ./data/loki_logs.json  # Use local file instead

# Tempo - for distributed traces
tempo_url: http://localhost:3200
# tempo_file: ./data/tempo_traces.json  # Use local file instead

# ============================================================================
# LLM Configuration (for AI-powered Root Cause Analysis)
# ============================================================================

# Enable AI explanation (equivalent to --explain flag)
explain: true

# Local LLM (Ollama) - recommended for privacy
llm_url: http://localhost:11434/v1
llm_model: llama3.1:8b

# Cloud LLM alternatives (set API keys as environment variables):
#   OPENAI_API_KEY - for OpenAI (llm_model: gpt-4o)
#   ANTHROPIC_API_KEY - for Anthropic (llm_model: claude-sonnet-4-5-20250514)

# ============================================================================
# Output Settings
# ============================================================================

# Path to save the analysis report (Markdown format)
output: ./reports/analysis.md

# File format (auto-detected if not specified)
# format: k6  # Options: jtl, k6, gatling, locust
'''
        output_path = args.output
        if os.path.exists(output_path):
            print(f"Error: {output_path} already exists. Use -o to specify a different path.")
            sys.exit(1)
        
        with open(output_path, 'w') as f:
            f.write(config_content)
        
        print(f"✓ Created config file: {output_path}")
        print(f"\nUsage: heimr analyze results.jtl -c {output_path}")
        sys.exit(0)

    elif args.command == "analyze":
        try:
            # Load config file if provided
            if args.config:
                config = load_config(args.config)
                args = merge_config_with_args(args, config)
                print(f"Loaded config from: {args.config}")
            
            # Detect format if not specified
            file_format = args.format
            if not file_format:
                ext = os.path.splitext(args.file)[1].lower()
                if ext == '.json':
                    file_format = 'k6'
                elif ext == '.log':
                    file_format = 'gatling'
                elif 'stats_history' in args.file:
                    file_format = 'locust'
                else:
                    file_format = 'jtl'

            # Select parser
            if file_format == 'k6':
                file_parser = K6Parser(args.file)
            elif file_format == 'gatling':
                file_parser = GatlingParser(args.file)
            elif file_format == 'locust':
                file_parser = LocustParser(args.file)
            else:
                file_parser = JTLParser(args.file)

            print_banner()
            
            print(f"Analyzing {args.file} ({file_format})...")
            df = file_parser.parse()
            stats = file_parser.get_summary_stats()
            
            # Calculate Extended Stats
            if not df.empty:
                stats['median_latency'] = df['elapsed'].median()
                stats['min_latency'] = df['elapsed'].min()
                stats['max_latency'] = df['elapsed'].max()
                stats['error_count'] = len(df[~df['success']])
                
                duration_sec = (stats['end_time'] - stats['start_time']).total_seconds()
                stats['throughput'] = stats['total_requests'] / duration_sec if duration_sec > 0 else 0
            
            if df.empty:
                print("No data found.")
                return

            # 2. Detect Anomalies
            detector = AnomalyDetector(df)
            anomalies = detector.detect_latency_anomalies()
            anomaly_summary = detector.get_anomaly_summary(anomalies)

            # Print Status
            print_status(stats, anomaly_summary)

            print("\n--- Test Summary ---")
            print(f"Total Requests: {stats.get('total_requests')}")
            print(f"Avg Latency: {stats.get('avg_latency'):.2f} ms")
            print(f"P99 Latency: {stats.get('p99_latency'):.2f} ms")
            print(f"Error Rate: {stats.get('error_rate'):.2f}%")
            
            print("\n--- Anomaly Details ---")
            print(f"Found {anomaly_summary['count']} latency anomalies.")
            if anomaly_summary['count'] > 0:
                print(f"Average Anomaly Latency: {anomaly_summary['avg_latency']:.2f} ms")
                print(f"Max Anomaly Latency: {anomaly_summary['max_latency']:.2f} ms")
                print("Anomaly Timestamps (first 5):")
                for ts in anomaly_summary['timestamps'][:5]:
                    print(f" - {ts}")

            # 3. Prometheus Metrics (Optional)
            prom_metrics = {}
            if args.prometheus_url or args.prometheus_file:
                print("\n--- Fetching Prometheus Metrics ---")
                try:
                    prom = PrometheusClient(url=args.prometheus_url or "http://localhost:9090", file_path=args.prometheus_file)
                    # Use a dummy time range for now, or infer from data
                    # For simplicity, we'll just fetch current metrics in this demo
                    prom_metrics = prom.get_system_metrics(stats['start_time'], stats['end_time'])
                    print(f"Fetched {len(prom_metrics)} metric types.")
                except Exception as e:
                    print(f"Warning: Failed to fetch Prometheus metrics: {e}")

            # 4. Loki Logs (Optional)
            loki_logs = []
            if args.loki_url or args.loki_file:
                print("\n--- Fetching Loki Logs ---")
                try:
                    loki = LokiClient(url=args.loki_url or "http://localhost:3100", file_path=args.loki_file)
                    loki_logs = loki.get_error_logs(stats['start_time'], stats['end_time'])
                    print(f"Fetched {len(loki_logs)} error logs.")
                except Exception as e:
                    print(f"Warning: Failed to fetch Loki logs: {e}")

            # 5. Tempo Traces (Optional)
            tempo_traces = []
            if args.tempo_url or args.tempo_file:
                print("\n--- Fetching Tempo Traces ---")
                try:
                    tempo = TempoClient(url=args.tempo_url or "http://localhost:3200", file_path=args.tempo_file)
                    # Fetch traces slower than P99 latency
                    min_duration = int(stats.get('p99_latency', 1000))
                    tempo_traces = tempo.get_slow_traces(stats['start_time'], stats['end_time'], min_duration_ms=min_duration)
                    print(f"Fetched {len(tempo_traces)} slow traces (> {min_duration}ms).")
                except Exception as e:
                    print(f"Warning: Failed to fetch Tempo traces: {e}")

            # Multi-Signal Detection: Check for failures across multiple signals
            failure_signals = []
            
            # Signal 1: Anomalies detected
            if anomaly_summary['count'] > 0:
                failure_signals.append(f"Anomalies: {anomaly_summary['count']}")
            
            # Signal 2: Error rate > 0%
            if stats.get('error_rate', 0) > 0:
                failure_signals.append(f"Error Rate: {stats['error_rate']:.2f}%")
            
            # Signal 3: High CPU usage in Prometheus
            if prom_metrics and 'cpu_usage' in prom_metrics and len(prom_metrics['cpu_usage']) > 0:
                cpu_values = [float(v[1]) for v in prom_metrics['cpu_usage'][0]['values']]
                avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                if avg_cpu > 0.8:  # 80% CPU
                    failure_signals.append(f"High CPU: {avg_cpu*100:.1f}%")
            
            # Signal 4: Memory growth in Prometheus
            if prom_metrics and 'memory_usage' in prom_metrics and len(prom_metrics['memory_usage']) > 0:
                mem_values = [int(v[1]) for v in prom_metrics['memory_usage'][0]['values']]
                if len(mem_values) >= 2:
                    mem_growth = (mem_values[-1] - mem_values[0]) / mem_values[0]
                    if mem_growth > 0.5:  # 50% growth
                        failure_signals.append(f"Memory Growth: {mem_growth*100:.1f}%")
            
            # Signal 5: ERROR/WARN logs in Loki
            if loki_logs:
                error_count = sum(1 for log in loki_logs if 'level=error' in log or 'level=warn' in log)
                if error_count > 0:
                    failure_signals.append(f"Error/Warn Logs: {error_count}")
            
            # Signal 6: Slow traces in Tempo (only if significantly above P99)
            # Don't flag if traces are just slightly above P99 (normal variance)
            if tempo_traces and len(tempo_traces) > 5:  # Only flag if > 5 slow traces
                # Check if slow traces are significantly slower (> 2x P99)
                p99 = stats.get('p99_latency', 1000)
                very_slow_traces = [t for t in tempo_traces if t.get('duration', 0) > p99 * 2]
                if len(very_slow_traces) > 0:
                    failure_signals.append(f"Very Slow Traces: {len(very_slow_traces)}")
            
            # Determine overall status
            has_failure = len(failure_signals) > 0
            status_icon = "❌" if has_failure else "✅"
            status_text = "FAILED" if has_failure else "PASSED"
            
            print(f"\\n--- Overall Status ---")
            print(f"# {status_icon} {status_text}")
            if has_failure:
                print(f"**Reasons**: {', '.join(failure_signals)}")
            else:
                print("No errors or anomalies detected.")

            # 6. Explain (Optional)
            full_explanation = ""
            if args.explain:
                print("\n--- AI Analysis (Heimr) ---")
                
                try:
                    llm = LLMClient(
                        base_url=args.llm_url,
                        model=args.llm_model
                    )
                    
                    print(f"Using LLM Provider: {llm.provider.upper()}")
                    if args.llm_url:
                        print(f"Model: {args.llm_model or 'llama3'}")
                    
                    # Pass metrics, logs, and traces to LLM
                    explanation_generator = llm.generate_explanation(stats, anomaly_summary, prom_metrics, loki_logs, tempo_traces)
                    
                    print("\n", end="", flush=True)
                    for chunk in explanation_generator:
                        print(chunk, end="", flush=True)
                        full_explanation += chunk
                    print("\n")
                except ValueError as e:
                    print(f"Error: {e}")

            # Save report if requested
            if args.output:
                with open(args.output, "w") as f:
                    # Generate header for file (no ANSI colors)
                    header = "```text\n"
                    header += """
   ▄▄▄  ▄▄▄                                    
  █▀██  ██                                     
    ██  ██         ▀▀ ▄        ▄             ▀▀
    ██████   ▄█▀█▄ ██ ███▄███▄ ████▄   ▄▀▀█▄ ██
    ██  ██   ██▄█▀ ██ ██ ██ ██ ██      ▄█▀██ ██
  ▀██▀  ▀██▄▄▀█▄▄▄▄██▄██ ██ ▀█▄█▀  ██ ▄▀█▄██▄██
"""
                    header += "```\n\n"
                    
                    # Use the multi-signal failure detection (same as console output)
                    if has_failure:
                        header += f"# {status_icon} {status_text}\n**Reasons**: {", ".join(failure_signals)}\n\n"
                    else:
                        header += f"# {status_icon} {status_text}\nNo errors or anomalies detected.\n\n"
                    
                    # Construct KPI Table
                    kpi_table = "| Metric | Value |\n|---|---|\n"
                    kpi_table += f"| Total Requests | {stats.get('total_requests')} |\n"
                    kpi_table += f"| Throughput | {stats.get('throughput', 0):.2f} req/s |\n"
                    kpi_table += f"| Error Rate | {stats.get('error_rate', 0):.2f}% ({stats.get('error_count', 0)} errors) |\n"
                    kpi_table += f"| Avg Latency | {stats.get('avg_latency', 0):.2f} ms |\n"
                    kpi_table += f"| Median Latency | {stats.get('median_latency', 0):.2f} ms |\n"
                    kpi_table += f"| P95 Latency | {stats.get('p95_latency', 0):.2f} ms |\n"
                    kpi_table += f"| P99 Latency | {stats.get('p99_latency', 0):.2f} ms |\n"
                    kpi_table += f"| Min Latency | {stats.get('min_latency', 0):.2f} ms |\n"
                    kpi_table += f"| Max Latency | {stats.get('max_latency', 0):.2f} ms |\n"

                    # Replace placeholder in full_explanation
                    if "[KPI_TABLE]" in full_explanation:
                        full_explanation = full_explanation.replace("[KPI_TABLE]", kpi_table)
                    else:
                        # Fallback if LLM didn't include placeholder
                        full_explanation = f"## Key Performance Indicators\n{kpi_table}\n\n" + full_explanation

                    f.write(header + full_explanation)
                print(f"✅ Report saved to: {args.output}")

            # Generate Dashboard if requested
            if args.dashboard:
                try:
                    from heimr.dashboard import DashboardGenerator
                    dashboard_gen = DashboardGenerator(df, stats, prom_metrics)
                    dashboard_gen.generate(args.dashboard)
                except Exception as e:
                    print(f"Warning: Failed to generate dashboard: {e}")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
