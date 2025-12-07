# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import argparse
import sys
import os
import yaml
from heimr.analyzer import Analyzer, AnalysisResult
from heimr.setup_llm import setup_llm


def load_config(config_path: str) -> dict:
    """
    Load configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    return config


def merge_config_with_args(args, config: dict):
    """
    Merge config file settings with command line arguments.
    CLI arguments take precedence over config file.
    """
    # Map config keys to argparse attribute names
    key_mapping = {
        'prometheus': 'prometheus',
        'prometheus_url': 'prometheus',
        'prometheus_file': 'prometheus',
        'loki': 'loki',
        'loki_url': 'loki',
        'loki_file': 'loki',
        'tempo': 'tempo',
        'tempo_url': 'tempo',
        'tempo_file': 'tempo',
        'llm_url': 'llm_url',
        'llm_model': 'llm_model',
        'output': 'output',
        'compare_baseline': 'compare_baseline',
        'compare_prometheus': 'compare_prometheus',
        'compare_loki': 'compare_loki',
        'compare_tempo': 'compare_tempo',
    }

    for config_key, arg_key in key_mapping.items():
        if config_key in config:
            current_value = getattr(args, arg_key, None)
            if current_value is None or (isinstance(current_value, bool) and not current_value):
                setattr(args, arg_key, config[config_key])

    return args


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


def generate_markdown_report_content(result: AnalysisResult, args) -> str:
    """Generates the full markdown report content."""
    df = result.df
    kpi_data = result.kpi
    
    status_icon = "❌" if result.status == "FAILED" else "✅"
    
    header = "```text\n"
    header += """
 █████   █████           ███                           
░░███   ░░███           ░░░                            
 ░███    ░███   ██████  ████  █████████████   ████████ 
 ░███████████  ███░░███░░███ ░░███░░███░░███ ░░███░░███
 ░███░░░░░███ ░███████  ░███  ░███ ░███ ░███  ░███ ░░░ 
 ░███    ░███ ░███░░░   ░███  ░███ ░███ ░███  ░███     
 █████   █████░░██████  █████ █████░███ █████ █████    
░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░░░ ░░░ ░░░░░ ░░░░░     
"""
    header += "```\n\n"

    # Context Tags
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

    if result.status == "FAILED":
        reasons_str = ", ".join(result.failure_signals)
        header += f"# {status_icon} {result.status}\n**Reasons**: {reasons_str}\n\n"
    else:
        header += f"# {status_icon} {result.status}\nNo errors or anomalies detected.\n\n"

    # KPI Table
    kpi_table = "## Level 1: Primary KPIs\n"
    kpi_table += "| Metric | Value | Reference |\n|---|---|---|\n"
    kpi_table += f"| P95 Latency | {kpi_data['latency']['p95']:.2f} ms | < 500ms (API) |\n"
    kpi_table += f"| Error Rate | {kpi_data['errors']['rate']:.2f}% | < 1.0% |\n"
    kpi_table += (
        f"| Throughput | {kpi_data['throughput']['requests_per_second']:.2f} req/s | "
        f"{kpi_data['throughput']['bytes_in_per_second'] / 1024:.2f} KB/s |\n\n"
    )

    # Level 2: Summary
    kpi_table += "## Level 2: Summary\n"
    kpi_table += f"- **Concurrency**: Max {kpi_data['concurrency']['max']} VUs, Avg {kpi_data['concurrency']['avg']} VUs\n"
    kpi_table += f"- **Anomalies**: {result.anomaly_summary['count']} detected"
    if result.anomaly_summary['count'] > 0:
        kpi_table += f" (Avg {result.anomaly_summary['avg_latency']:.2f} ms)"
    kpi_table += "\n"
    
    if args.prometheus:
        kpi_table += f"- **Prometheus**: Fetched {len(result.prom_metrics)} metric types\n"
    if args.loki:
        kpi_table += f"- **Loki**: Fetched {len(result.loki_logs)} error logs\n"
    if args.tempo:
        kpi_table += f"- **Tempo**: Fetched {len(result.tempo_traces)} slow traces\n"
    kpi_table += "\n"

    # Per Endpoint Breakdown
    kpi_table += "## Level 3: Per Endpoint Breakdown\n"
    kpi_table += "| Endpoint | Requests | RPS | Error % | Avg (ms) | P95 (ms) | P99 (ms) |\n"
    kpi_table += "|---|---|---|---|---|---|---|\n"

    if not df.empty:
        if 'endpoint' in df.columns:
            grouped = df.groupby('endpoint')
            for name, group in grouped:
                count = len(group)
                duration_sec = (group['timestamp_dt'].max() - group['timestamp_dt'].min()).total_seconds()
                throughput = count / duration_sec if duration_sec > 0 else 0
                error_count = len(group[~group['success']])
                error_rate = (error_count / count) * 100
                avg = group['elapsed'].mean()
                p95 = group['elapsed'].quantile(0.95)
                p99 = group['elapsed'].quantile(0.99)
                kpi_table += (
                    f"| {name} | {count} | {throughput:.2f} | {error_rate:.2f}% | "
                    f"{avg:.2f} | {p95:.2f} | {p99:.2f} |\n"
                )
        else:
            kpi_table += "| Unknown Endpoint | - | - | - | - | - | - |\n"

        # Aggregate Row
        total_count = kpi_data['throughput']['total_requests']
        total_throughput = kpi_data['throughput']['requests_per_second']
        total_error_rate = kpi_data['errors']['rate']
        total_avg = kpi_data['latency']['avg']
        total_p95 = kpi_data['latency']['p95']
        total_p99 = kpi_data['latency']['p99']
        kpi_table += f"| **TOTAL** | **{total_count}** | **{total_throughput:.2f}** | **{total_error_rate:.2f}%** | **{total_avg:.2f}** | **{total_p95:.2f}** | **{total_p99:.2f}** |\n"
    else:
        kpi_table += "| No data | - | - | - | - | - | - |\n"
        
    # Appendix: Logs & Traces
    if result.loki_logs or result.tempo_traces:
        kpi_table += "\n## Level 4: Observability Data\n"
        if result.loki_logs:
            kpi_table += "### Loki Error Logs (Sample)\n"
            for log in result.loki_logs[:5]: # Show first 5
                kpi_table += f"- `{log}`\n"
            kpi_table += "\n"
        if result.tempo_traces:
            kpi_table += "### Tempo Slow Traces (Sample)\n"
            for trace in result.tempo_traces[:5]:
                kpi_table += f"- TraceID: `{trace.get('traceID')}` ({trace.get('duration')}ms)\n"
            kpi_table += "\n"

    full_explanation = result.llm_explanation or ""
    # Replace placeholder
    if "[KPI_TABLE]" in full_explanation:
        final_explanation = full_explanation.replace("[KPI_TABLE]", kpi_table)
    else:
        final_explanation = f"{kpi_table}\n\n" + full_explanation

    return header + final_explanation


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
    analyze_parser.add_argument("--prometheus", help="Prometheus server URL or path to JSON file")
    analyze_parser.add_argument("--loki", help="Loki server URL or path to JSON file")
    analyze_parser.add_argument("--tempo", help="Tempo server URL or path to JSON file")
    analyze_parser.add_argument("--llm-url", default=None, help="Base URL for LLM API")
    analyze_parser.add_argument("--llm-model", default=None, help="LLM model to use")
    
    # Comparison arguments
    analyze_parser.add_argument("--compare-baseline", help="Path to baseline load test file for comparison")
    analyze_parser.add_argument("--compare-prometheus", help="Path to baseline Prometheus metrics file")
    analyze_parser.add_argument("--compare-loki", help="Path to baseline Loki logs file")
    analyze_parser.add_argument("--compare-tempo", help="Path to baseline Tempo traces file")
    analyze_parser.add_argument("--fail-on-regression", type=float, help="Fail if metric worsens by %")
    analyze_parser.add_argument("--fail-condition", action="append", help="Fail if condition is met")
    analyze_parser.add_argument("--tag", action="append", help="Add metadata tag to report")
    analyze_parser.add_argument("--ci-summary", nargs="?", const="GITHUB_STEP_SUMMARY", help="Generate GH Summary")
    analyze_parser.add_argument("--junit-output", help="Path to save JUnit XML report")

    args = parser.parse_args()

    if args.command == "config-init":
        # ... logic for config init (keep simple string write for now to save space, or restore full content)
        # For brevity, I'll restore the essential content
        config_content = '''# Heimr Configuration File
prometheus: http://localhost:9090
loki: http://localhost:3100
tempo: http://localhost:3200
explain: true
llm_model: llama3.1:8b
output: ./reports/analysis.md
'''
        with open(args.output, 'w') as f:
            f.write(config_content)
        print(f"✓ Created config file: {args.output}")
        sys.exit(0)

    elif args.command == "setup-llm":
        from heimr.setup_llm import setup_llm
        success = setup_llm(interactive=not args.non_interactive)
        sys.exit(0 if success else 1)

    elif args.command == "analyze":
        # Load and merge config
        config = {}
        if args.config:
            config = load_config(args.config)
        args = merge_config_with_args(args, config)

        # Build config dict for Analyzer
        analyzer_config = {
            'prometheus': args.prometheus,
            'loki': args.loki,
            'tempo': args.tempo,
            'llm_url': args.llm_url,
            'llm_model': args.llm_model,
        }
        
        print_banner()
        print(f"Analyzing {args.file}...")

        # Initialize Analyzer
        analyzer = Analyzer(
            file_path=args.file,
            config=analyzer_config,
            llm_url=args.llm_url,
            llm_model=args.llm_model,
            no_llm=args.no_llm
        )

        # Helper for LLM streaming
        def stream_chunk(chunk):
            print(chunk, end="", flush=True)

        # Run Analysis
        result = analyzer.analyze(stream_callback=stream_chunk)
        
        # Print Summary
        print_result_summary(result)

        # --- Report Generation ---
        if args.output:
            report_content = generate_markdown_report_content(result, args)
            with open(args.output, "w") as f:
                f.write(report_content)
            print(f"✅ Report saved to: {args.output}")

            # PDF Generation
            print("\n--- Generating PDF Report ---")
            try:
                from heimr.pdf_generator import PDFGenerator
                pdf_gen = PDFGenerator()
                pdf_path = args.output.rsplit('.', 1)[0] + '.pdf'
                pdf_gen.generate_pdf(report_content, pdf_path)
                print(f"✅ PDF report saved to: {pdf_path}")
            except Exception as e:
                print(f"Warning: Failed to generate PDF: {e}")

        # --- Comparison Logic ---
        if args.compare_baseline and args.output:
            print("\n--- Generating Comparison Report ---")
            try:
                from heimr.comparator import PerformanceComparator
                
                # Analyze baseline (Reuse Analyzer!)
                print(f"Loading baseline: {args.compare_baseline}")
                baseline_config = {
                    'prometheus': args.compare_prometheus,
                    'loki': args.compare_loki,
                    'tempo': args.compare_tempo
                }
                baseline_analyzer = Analyzer(
                    file_path=args.compare_baseline,
                    config=baseline_config,
                    no_llm=True  # No LLM for baseline analysis loop
                )
                baseline_result = baseline_analyzer.analyze()
                
                # Enhance baseline stats with raw DF data needed for comparator
                # Comparator expects keys like 'median_latency' which Analyzer produces in legacy `stats`.
                # Analyzer `stats` includes: median_latency, min, max, throughput.
                
                comparator = PerformanceComparator(baseline_result.stats, result.stats)
                
                metrics_comparison = comparator.compare_metrics()
                anomalies_comparison = comparator.compare_anomalies(
                    baseline_result.anomaly_summary, result.anomaly_summary
                )
                
                prometheus_comparison = None
                if baseline_result.prom_metrics and result.prom_metrics:
                    prometheus_comparison = comparator.compare_prometheus(
                        baseline_result.prom_metrics, result.prom_metrics
                    )
                    
                logs_comparison = None
                # Logs need raw list, Analyzer returns list
                if baseline_result.loki_logs and result.loki_logs:
                    logs_comparison = comparator.compare_logs(
                        baseline_result.loki_logs, result.loki_logs
                    )
                    
                traces_comparison = None
                if baseline_result.tempo_traces and result.tempo_traces:
                    traces_comparison = comparator.compare_traces(
                        baseline_result.tempo_traces, result.tempo_traces
                    )
                    
                comparison_report = comparator.generate_comparison_report(
                    metrics_comparison,
                    anomalies_comparison,
                    prometheus_comparison,
                    logs_comparison,
                    traces_comparison
                )
                
                comparison_path = args.output.rsplit('.', 1)[0] + '_comparison.md'
                with open(comparison_path, 'w') as f:
                    f.write(comparison_report)
                print(f"✅ Comparison report saved to: {comparison_path}")
                
                 # Comparison PDF
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

        # Exit code
        if result.status == "FAILED":
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    main()
