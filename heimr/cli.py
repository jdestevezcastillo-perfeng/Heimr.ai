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
        'prometheus': 'prometheus',
        'prometheus_url': 'prometheus',  # Backward compatibility
        'prometheus_file': 'prometheus',  # Backward compatibility
        'loki': 'loki',
        'loki_url': 'loki',  # Backward compatibility
        'loki_file': 'loki',  # Backward compatibility
        'tempo': 'tempo',
        'tempo_url': 'tempo',  # Backward compatibility
        'tempo_file': 'tempo',  # Backward compatibility
        'llm_url': 'llm_url',
        'llm_model': 'llm_model',
        'output': 'output',
        'format': 'format',
        'compare_baseline': 'compare_baseline',
        'compare_prometheus': 'compare_prometheus',
        'compare_loki': 'compare_loki',
        'compare_tempo': 'compare_tempo',
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
        print(f"\033[1;31m❌ FAILED\033[0m")
        print(f"Reasons: {', '.join(reasons)}")
    else:
        print(f"\033[1;32m✅ PASSED\033[0m")
        print("No errors or anomalies detected.")
    print("="*50 + "\n")

def parse_url_or_file(value):
    """
    Parse a value that could be either a URL or a file path.
    Returns a tuple of (url, file_path) where one is None.
    """
    if not value:
        return None, None
    
    # Check if it's a URL
    if value.startswith('http://') or value.startswith('https://'):
        return value, None
    else:
        # It's a file path
        return None, value

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
    config_parser.add_argument("--output", "-o", default="heimr.yaml", help="Output path for the config file (default: heimr.yaml)")

    # Setup-LLM command
    setup_parser = subparsers.add_parser(
        "setup-llm",
        help="Setup Ollama and Llama 3.1 for AI analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    setup_parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode (auto-install)")


    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a load test result file and detect anomalies.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35, width=120)
    )
    analyze_parser.add_argument("file", help="Path to the load test result file (supports .jtl, .json, .log, .csv)")
    analyze_parser.add_argument("--config", "-c", metavar="FILE", help="""Path to YAML config file. Available keys:
  prometheus, loki, tempo, llm_url, llm_model,
  output, format, compare_baseline, compare_prometheus,
  compare_loki, compare_tempo.
  Run 'heimr config-init' to generate a template.
  Note: AI analysis is enabled by default. PDFs and HTML dashboards are auto-generated.""")
    analyze_parser.add_argument("--format", choices=['jtl', 'k6', 'gatling', 'locust'], help="Explicitly specify the file format (auto-detected by default)")
    analyze_parser.add_argument("--output", help="Path to save the generated analysis report (Markdown format)")
    analyze_parser.add_argument("--no-llm", action="store_true", help="Disable AI-powered analysis (enabled by default)")
    analyze_parser.add_argument("--prometheus", help="Prometheus server URL or path to JSON file (e.g., http://localhost:9090 or ./metrics.json)")
    analyze_parser.add_argument("--loki", help="Loki server URL or path to JSON file (e.g., http://localhost:3100 or ./logs.json)")
    analyze_parser.add_argument("--tempo", help="Tempo server URL or path to JSON file (e.g., http://localhost:3200 or ./traces.json)")
    analyze_parser.add_argument("--llm-url", default=None, help="Base URL for LLM API (default: http://localhost:11434/v1 if no API keys present)")
    analyze_parser.add_argument("--llm-model", default=None, help="""LLM model to use. Options:
  - small:  llama3.2:3b  (~2GB, laptops/CI/CD)
  - medium: llama3.1:8b  (~5GB, balanced) [DEFAULT]
  - large:  llama3.3:70b (~21GB, RTX 4090+, best quality)
  Or specify any model name directly (e.g., llama3.1:405b, gpt-4o)""")
    
    
    # Comparison arguments
    analyze_parser.add_argument("--compare-baseline", help="Path to baseline load test file for comparison")
    analyze_parser.add_argument("--compare-prometheus", help="Path to baseline Prometheus metrics file for comparison")
    analyze_parser.add_argument("--compare-loki", help="Path to baseline Loki logs file for comparison")
    analyze_parser.add_argument("--compare-tempo", help="Path to baseline Tempo traces file for comparison")
    analyze_parser.add_argument("--fail-on-regression", type=float, help="Fail if any metric worsens by more than this percentage (requires --compare-baseline)")
    analyze_parser.add_argument("--fail-condition", action="append", help="Fail if condition is met (e.g. 'p99_latency > 500', 'error_rate > 1.0'). Can be used multiple times.")
    analyze_parser.add_argument("--tag", action="append", help="Add metadata tag to report (e.g. 'commit=sha123', 'branch=main')")
    analyze_parser.add_argument("--ci-summary", nargs="?", const="GITHUB_STEP_SUMMARY", help="Generate GitHub Actions Step Summary (optional: file path)")
    analyze_parser.add_argument("--junit-output", help="Path to save JUnit XML report")



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
# Can be a URL or a file path
prometheus: http://localhost:9090
# prometheus: ./data/prometheus_metrics.json  # Or use local file

# Loki - for log aggregation
# Can be a URL or a file path
loki: http://localhost:3100
# loki: ./data/loki_logs.json  # Or use local file

# Tempo - for distributed traces
# Can be a URL or a file path
tempo: http://localhost:3200
# tempo: ./data/tempo_traces.json  # Or use local file


# ============================================================================
# LLM Configuration (for AI-powered Root Cause Analysis)
# ============================================================================

# Enable AI explanation (equivalent to --explain flag)
explain: true

# Local LLM (Ollama) - recommended for privacy
# llm_url: http://localhost:11434/v1
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

    elif args.command == "setup-llm":
        # Setup Ollama and Llama 3.1
        from heimr.setup_llm import setup_llm
        success = setup_llm(interactive=not args.non_interactive)
        sys.exit(0 if success else 1)

    elif args.command == "analyze":
        try:
            # Load config file if provided
            if args.config:
                config = load_config(args.config)
                args = merge_config_with_args(args, config)
                print(f"Loaded config from: {args.config}")
            
            # Smart LLM URL Detection
            # If user didn't specify URL, and no API keys are present, default to Local Ollama.
            # If keys ARE present, leave URL as None so LLMClient chooses Cloud Provider.
            if not args.llm_url:
                has_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
                if not has_api_key:
                    args.llm_url = "http://localhost:11434/v1"
            
            # Set default model if not configured
            if not args.llm_model:
                args.llm_model = "medium"
            
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
                elif args.file.endswith('.har'):
                    file_format = 'har'
                else:
                    # Try to detect HAR by content
                    try:
                        with open(args.file, 'r') as f:
                            first_chars = f.read(100)
                            if '"log"' in first_chars and '"entries"' in first_chars:
                                file_format = 'har'
                            else:
                                file_format = 'jtl'
                    except:
                        file_format = 'jtl'

            # Select parser
            if file_format == 'k6':
                file_parser = K6Parser(args.file)
            elif file_format == 'gatling':
                file_parser = GatlingParser(args.file)
            elif file_format == 'locust':
                file_parser = LocustParser(args.file)
            elif file_format == 'har':
                from heimr.parsers.har import HARParser
                file_parser = HARParser(args.file)
            else:
                file_parser = JTLParser(args.file)

            print_banner()
            
            print(f"Analyzing {args.file} ({file_format})...")
            df = file_parser.parse()
            
            # --- KPI Engine Integration ---
            from heimr.kpi import KPIEngine
            kpi = KPIEngine(df)
            kpi_data = kpi.get_kpi_dict()
            
            # Legacy stats adapter for existing consumers (detectors, etc)
            stats = {
                'total_requests': kpi_data['throughput']['total_requests'],
                'start_time': df['timestamp_dt'].min() if not df.empty else None,
                'end_time': df['timestamp_dt'].max() if not df.empty else None,
                'avg_latency': kpi_data['latency']['avg'],
                'p95_latency': kpi_data['latency']['p95'],
                'p99_latency': kpi_data['latency']['p99'],
                'p50_latency': kpi_data['latency']['p50'], # Explicit P50
                'error_rate': kpi_data['errors']['rate'],
                'median_latency': kpi_data['latency']['p50'],
                'min_latency': kpi_data['latency']['min'],
                'max_latency': kpi_data['latency']['max'],
                'throughput': kpi_data['throughput']['requests_per_second']
            }
            
            if df.empty:
                print("No data found.")
                return

            # 2. Detect Anomalies
            detector = AnomalyDetector(df)
            anomalies = detector.detect_latency_anomalies()
            anomaly_summary = detector.get_anomaly_summary(anomalies)

            # --- REPORT SPECIFICATION: LEVEL 1 (Header) ---
            print("\n" + "="*50)
            print("HEIMR REPORT (Level 1)")
            print("="*50)
            print(f"{'Metric':<25} | {'Value':<15}")
            print("-" * 43)
            print(f"{'Result':<25} | {'PENDING'}") # Placeholder
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

            # 3. Prometheus Metrics (Optional)
            prom_metrics = {}
            if args.prometheus:
                print("\n--- Fetching Prometheus Metrics ---")
                try:
                    prom_url, prom_file = parse_url_or_file(args.prometheus)
                    prom = PrometheusClient(url=prom_url or "http://localhost:9090", file_path=prom_file)
                    # Use a dummy time range for now, or infer from data
                    # For simplicity, we'll just fetch current metrics in this demo
                    prom_metrics = prom.get_system_metrics(stats['start_time'], stats['end_time'])
                    print(f"Fetched {len(prom_metrics)} metric types.")
                except Exception as e:
                    print(f"Warning: Failed to fetch Prometheus metrics: {e}")

            # 4. Loki Logs (Optional)
            loki_logs = []
            if args.loki:
                print("\n--- Fetching Loki Logs ---")
                try:
                    loki_url, loki_file = parse_url_or_file(args.loki)
                    loki = LokiClient(url=loki_url or "http://localhost:3100", file_path=loki_file)
                    loki_logs = loki.get_error_logs(stats['start_time'], stats['end_time'])
                    print(f"Fetched {len(loki_logs)} error logs.")
                except Exception as e:
                    print(f"Warning: Failed to fetch Loki logs: {e}")

            # 5. Tempo Traces (Optional)
            tempo_traces = []
            if args.tempo:
                print("\n--- Fetching Tempo Traces ---")
                try:
                    tempo_url, tempo_file = parse_url_or_file(args.tempo)
                    tempo = TempoClient(url=tempo_url or "http://localhost:3200", file_path=tempo_file)
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

            # 6. AI Analysis (enabled by default)
            full_explanation = ""
            if not args.no_llm:
                print("\n--- AI Analysis (Heimr) ---")
                
                try:
                    llm = LLMClient(
                        base_url=args.llm_url,
                        model=args.llm_model
                    )
                    
                    print(f"Using LLM Provider: {llm.provider.upper()}")
                    print(f"Model: {args.llm_model}")
                    
                    # Pass metrics, logs, and traces to LLM
                    explanation_generator = llm.generate_explanation(stats, anomaly_summary, prom_metrics, loki_logs, tempo_traces)
                    
                    print("\n", end="", flush=True)
                    for chunk in explanation_generator:
                        print(chunk, end="", flush=True)
                        full_explanation += chunk
                    print("\n")
                except ValueError as e:
                    print(f"Error: {e}")
                    print("Tip: Make sure Ollama is running with: ollama serve")
                except Exception as e:
                    print(f"Warning: LLM analysis failed: {e}")
                    print("Continuing with statistical analysis only...")
            
            # --- CLI Exit Code Logic based on Gating ---
            # Revisit fail-on-regression later (requires comparator), for now check absolute conditions if provided
            if args.fail_condition:
                 # Minimal check
                 pass

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
  ▀██▀  ▀██▄▄▀█▄▄▄▄██▄██ ██ ██ ▀█▄█▀  ██ ▄▀█▄██▄██
"""
                    header += "```\n\n"
                    
                    # 0. Context Tags
                    if args.tag:
                        header += "### Build Context\n"
                        header += "| Key | Value |\n|---|---|\n"
                        for tag in args.tag:
                            if '=' in tag:
                                k, v = tag.split('=', 1)
                                header += f"| **{k}** | `{v}` |\n"
                            else:
                                header += f"| **Tag** | `{tag}` |\n"
                        header += "\n"
                    
                    # Use the multi-signal failure detection (same as console output)
                    if has_failure:
                        reasons_str = ", ".join(failure_signals)
                        header += f"# {status_icon} {status_text}\n**Reasons**: {reasons_str}\n\n"
                    else:
                        header += f"# {status_icon} {status_text}\nNo errors or anomalies detected.\n\n"
                    
                    # Construct KPI Table (Per Endpoint)
                    # LEVEL 1 Table for Report
                    kpi_table = "## Level 1: Primary KPIs\n"
                    kpi_table += "| Metric | Value | Threshold (Ref) |\n|---|---|---|\n"
                    kpi_table += f"| P95 Latency | {kpi_data['latency']['p95']:.2f} ms | < 500ms (API) |\n" 
                    kpi_table += f"| Error Rate | {kpi_data['errors']['rate']:.2f}% | < 1.0% |\n"
                    kpi_table += f"| Throughput | {kpi_data['throughput']['requests_per_second']:.2f} req/s | {kpi_data['throughput']['bytes_in_per_second']/1024:.2f} KB/s in |\n\n"

                    # Level 2 Details
                    kpi_table += "## Level 3: Per Endpoint Breakdown\n"
                    kpi_table += "| Endpoint | Requests | RPS | Error % | Avg (ms) | P95 (ms) | P99 (ms) |\n"
                    kpi_table += "|---|---|---|---|---|---|---|\n"
                    
                    if not df.empty:
                        # Check if 'name' column exists (it does from UnifiedSchema: 'endpoint')
                        if 'endpoint' in df.columns:
                            # Group by endpoint (name)
                            grouped = df.groupby('endpoint')
                            for name, group in grouped:
                                count = len(group)
                                # Duration for this specific endpoint's activity
                                duration_sec = (group['timestamp_dt'].max() - group['timestamp_dt'].min()).total_seconds()
                                throughput = count / duration_sec if duration_sec > 0 else 0
                                
                                error_count = len(group[~group['success']])
                                error_rate = (error_count / count) * 100
                                
                                avg = group['elapsed'].mean()
                                p95 = group['elapsed'].quantile(0.95)
                                p99 = group['elapsed'].quantile(0.99)
                                
                                kpi_table += f"| {name} | {count} | {throughput:.2f} | {error_rate:.2f}% | {avg:.2f} | {p95:.2f} | {p99:.2f} |\n"
                        else:
                            print(f"Warning: 'endpoint' column not found in DataFrame. Columns: {df.columns.tolist()}")
                            kpi_table += "| Unknown Endpoint | - | - | - | - | - | - |\n"
                        
                        # Add Aggregate Row
                        total_count = kpi_data['throughput']['total_requests']
                        total_throughput = kpi_data['throughput']['requests_per_second']
                        total_error_rate = kpi_data['errors']['rate']
                        total_avg = kpi_data['latency']['avg']
                        total_p95 = kpi_data['latency']['p95']
                        total_p99 = kpi_data['latency']['p99']
                        
                        kpi_table += f"| **TOTAL** | **{total_count}** | **{total_throughput:.2f}** | **{total_error_rate:.2f}%** | **{total_avg:.2f}** | **{total_p95:.2f}** | **{total_p99:.2f}** |\n"
                    else:
                        kpi_table += "| No data | - | - | - | - | - | - |\n"

                    # Replace placeholder in full_explanation
                    if "[KPI_TABLE]" in full_explanation:
                        full_explanation = full_explanation.replace("[KPI_TABLE]", kpi_table)
                    else:
                        # Fallback if LLM didn't include placeholder
                        full_explanation = f"{kpi_table}\n\n" + full_explanation


                    f.write(header + full_explanation)
                print(f"✅ Report saved to: {args.output}")
                
                # Automatically generate PDF alongside markdown
                print("\n--- Generating PDF Report ---")
                try:
                    from heimr.pdf_generator import PDFGenerator
                    pdf_gen = PDFGenerator()
                    
                    # Read the markdown report we just saved
                    with open(args.output, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                    
                    # Generate PDF with same name but .pdf extension
                    pdf_path = args.output.rsplit('.', 1)[0] + '.pdf'
                    pdf_gen.generate_pdf(markdown_content, pdf_path)
                    print(f"✅ PDF report saved to: {pdf_path}")
                except Exception as e:
                    print(f"Warning: Failed to generate PDF: {e}")

                # Automatically generate HTML dashboard alongside markdown
                print("\n--- Generating HTML Dashboard ---")
                try:
                    from heimr.dashboard import DashboardGenerator
                    dashboard_gen = DashboardGenerator(df, stats, prom_metrics)
                    dashboard_path = args.output.rsplit('.', 1)[0] + '.html'
                    dashboard_gen.generate(dashboard_path)
                    print(f"✅ Dashboard saved to: {dashboard_path}")
                except Exception as e:
                    print(f"Warning: Failed to generate dashboard: {e}")


            # Generate Comparison Report if requested
            if args.compare_baseline and args.output:
                print("\n--- Generating Comparison Report ---")
                try:
                    from heimr.comparator import PerformanceComparator
                    
                    # Load baseline data
                    print(f"Loading baseline: {args.compare_baseline}")
                    baseline_format = args.format or 'k6'  # Use same format as current
                    
                    if baseline_format == 'k6':
                        baseline_parser = K6Parser(args.compare_baseline)
                    elif baseline_format == 'gatling':
                        baseline_parser = GatlingParser(args.compare_baseline)
                    elif baseline_format == 'locust':
                        baseline_parser = LocustParser(args.compare_baseline)
                    else:
                        baseline_parser = JTLParser(args.compare_baseline)
                    
                    baseline_df = baseline_parser.parse()
                    baseline_stats = baseline_parser.get_summary_stats()
                    
                    # Calculate extended baseline stats
                    if not baseline_df.empty:
                        baseline_stats['median_latency'] = baseline_df['elapsed'].median()
                        baseline_stats['min_latency'] = baseline_df['elapsed'].min()
                        baseline_stats['max_latency'] = baseline_df['elapsed'].max()
                        baseline_stats['error_count'] = len(baseline_df[~baseline_df['success']])
                        duration_sec = (baseline_stats['end_time'] - baseline_stats['start_time']).total_seconds()
                        baseline_stats['throughput'] = baseline_stats['total_requests'] / duration_sec if duration_sec > 0 else 0
                    
                    # Detect baseline anomalies
                    baseline_detector = AnomalyDetector(baseline_df)
                    baseline_anomalies_result = baseline_detector.detect_latency_anomalies()
                    baseline_anomaly_summary = baseline_detector.get_anomaly_summary(baseline_anomalies_result)
                    
                    # Load baseline observability data
                    baseline_prom_metrics = {}
                    baseline_loki_logs = []
                    baseline_tempo_traces = []
                    
                    if args.compare_prometheus:
                        print(f"Loading baseline Prometheus metrics: {args.compare_prometheus}")
                        import json
                        with open(args.compare_prometheus, 'r') as f:
                            baseline_prom_metrics = json.load(f)
                    
                    if args.compare_loki:
                        print(f"Loading baseline Loki logs: {args.compare_loki}")
                        import json
                        with open(args.compare_loki, 'r') as f:
                            loki_data = json.load(f)
                            if 'data' in loki_data and 'result' in loki_data['data']:
                                for stream in loki_data['data']['result']:
                                    for value in stream['values']:
                                        baseline_loki_logs.append(value[1])
                    
                    if args.compare_tempo:
                        print(f"Loading baseline Tempo traces: {args.compare_tempo}")
                        import json
                        with open(args.compare_tempo, 'r') as f:
                            tempo_data = json.load(f)
                            baseline_tempo_traces = tempo_data.get('data', [])
                    
                    # Create comparator and run comparison
                    comparator = PerformanceComparator(baseline_stats, stats)
                    
                    metrics_comparison = comparator.compare_metrics()
                    anomalies_comparison = comparator.compare_anomalies(baseline_anomaly_summary, anomaly_summary)
                    
                    prometheus_comparison = None
                    if baseline_prom_metrics and prom_metrics:
                        prometheus_comparison = comparator.compare_prometheus(baseline_prom_metrics, prom_metrics)
                    
                    logs_comparison = None
                    if baseline_loki_logs and loki_logs:
                        logs_comparison = comparator.compare_logs(baseline_loki_logs, loki_logs)
                    
                    traces_comparison = None
                    if baseline_tempo_traces and tempo_traces:
                        traces_comparison = comparator.compare_traces(baseline_tempo_traces, tempo_traces)
                    
                    # Generate comparison report
                    comparison_report = comparator.generate_comparison_report(
                        metrics_comparison,
                        anomalies_comparison,
                        prometheus_comparison,
                        logs_comparison,
                        traces_comparison
                    )
                    
                    # Auto-generate comparison path based on output path
                    comparison_path = args.output.rsplit('.', 1)[0] + '_comparison.md'
                    
                    # Save comparison report
                    with open(comparison_path, 'w') as f:
                        f.write(comparison_report)
                    
                    print(f"✅ Comparison report saved to: {comparison_path}")
                    
                    # Automatically generate PDF for comparison report
                    try:
                        from heimr.pdf_generator import PDFGenerator
                        pdf_gen = PDFGenerator()
                        pdf_path = comparison_path.rsplit('.', 1)[0] + '.pdf'
                        pdf_gen.generate_pdf(comparison_report, pdf_path)
                        print(f"✅ Comparison PDF saved to: {pdf_path}")
                    except Exception as e:
                        print(f"Warning: Failed to generate comparison PDF: {e}")
                    
                except Exception as e:
                    print(f"Warning: Failed to generate comparison report: {e}")
                    import traceback
                    traceback.print_exc()

            # --- Performance Gating ---
            exit_code = 0
            
            # 1. Absolute Thresholds (Fail Conditions)
            if args.fail_condition:
                print("\n--- Checking Failure Conditions ---")
                for condition in args.fail_condition:
                    try:
                        # Parse "metric op value"
                        parts = condition.split()
                        if len(parts) != 3:
                            print(f"⚠️ Invalid condition format: '{condition}'. Expected 'metric op value' (e.g. 'p99_latency > 500')")
                            continue
                            
                        metric, op, limit_str = parts[0].lower(), parts[1], parts[2]
                        limit = float(limit_str)
                        
                        # Map friendly names to stat keys
                        metric_map = {
                            'p99': 'p99_latency',
                            'p95': 'p95_latency',
                            'avg': 'avg_latency',
                            'error': 'error_rate',
                            'requests': 'total_requests',
                            'rps': 'throughput'
                        }
                        # Allow partial matches like 'p99' mapping to 'p99_latency'
                        stat_key = metric
                        if metric in metric_map:
                            stat_key = metric_map[metric]
                        
                        if stat_key not in stats:
                            print(f"⚠️ Metric '{metric}' not found in results.")
                            continue
                            
                        actual_value = float(stats[stat_key])
                        
                        failed = False
                        if op == '>': failed = actual_value > limit
                        elif op == '>=': failed = actual_value >= limit
                        elif op == '<': failed = actual_value < limit
                        elif op == '<=': failed = actual_value <= limit
                        elif op == '==': failed = actual_value == limit
                        
                        if failed:
                            print(f"❌ FAILED: {metric} ({actual_value:.2f}) {op} {limit}")
                            exit_code = 1
                        else:
                            print(f"✅ PASSED: {metric} ({actual_value:.2f}) not {op} {limit}")
                            
                    except ValueError:
                        print(f"⚠️ Error parsing value in condition: '{condition}'")
            
            # 2. Regression Check (Fail on Regression)
            if args.fail_on_regression:
                if not args.compare_baseline:
                    print("\n⚠️ --fail-on-regression ignored because --compare-baseline was not provided.")
                elif 'comparator' in locals() and 'metrics_comparison' in locals():
                    # We have a comparator and metrics from the comparison block above
                    print(f"\n--- Checking Regression Threshold ({args.fail_on_regression}%) ---")
                    
                    # Reuse the logic we added to comparator
                    result = comparator.check_failure_conditions(metrics_comparison, fail_on_regression=args.fail_on_regression)
                    
                    if result['failed']:
                        for reason in result['reasons']:
                            print(f"❌ {reason}")
                        exit_code = 1
                        print("✅ No significant regressions detected.")
            
            # --- Reporters ---
            
            # Parse Tags
            tags = {}
            if args.tag:
                for tag in args.tag:
                    if '=' in tag:
                        k, v = tag.split('=', 1)
                        tags[k] = v
                    else:
                        tags[tag] = "true"

            # GitHub Summary
            if args.ci_summary:
                try:
                    from heimr.reporters.github import GitHubReporter
                    path = args.ci_summary if args.ci_summary != "GITHUB_STEP_SUMMARY" else None
                    gh_reporter = GitHubReporter(path)
                    
                    # Collect failure reasons (both from manual checks and logic above)
                    all_reasons = []
                    # Multi-signal failures
                    if 'failure_signals' in locals() and failure_signals:
                        all_reasons.extend(failure_signals)
                    # Gating failures (if any distinct ones)
                    # Note: failure_signals constructs strings like "Error Rate: ...", which are good
                    # But explicit gating failures like "p99 > 500" should also be included if separate
                    # Currently console prints them but doesn't store them in a list accessible here easily
                    # Hack: We printed them. Ideally refactor to collect them.
                    
                    gh_reporter.generate_summary(stats, anomaly_summary, all_reasons, tags)
                    print(f"✅ GitHub Summary generated.")
                except Exception as e:
                    print(f"Warning: Failed to generate GitHub Summary: {e}")

            # JUnit XML
            if args.junit_output:
                try:
                    from heimr.reporters.junit import JUnitReporter
                    junit = JUnitReporter(args.junit_output)
                    
                    all_reasons = []
                    if 'failure_signals' in locals() and failure_signals:
                        all_reasons.extend(failure_signals)
                        
                    junit.generate_report(stats, anomaly_summary, all_reasons, tags)
                except Exception as e:
                    print(f"Warning: Failed to generate JUnit report: {e}")

            if exit_code != 0:
                print("\n❌ Build Failed due to Performance Gating.")
                sys.exit(exit_code)

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
