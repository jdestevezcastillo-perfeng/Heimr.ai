import argparse
import sys
import os
from heimr.parsers.jtl import JTLParser
from heimr.parsers.k6 import K6Parser
from heimr.parsers.gatling import GatlingParser
from heimr.parsers.locust import LocustParser
from heimr.detector import AnomalyDetector
from heimr.llm import LLMClient
from heimr.prometheus import PrometheusClient

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

def main():
    parser = argparse.ArgumentParser(description="Heimr.ai - AI-Powered Load Test Analysis")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a load test result file and detect anomalies.")
    analyze_parser.add_argument("file", help="Path to the load test result file (supports .jtl, .json, .log, .csv)")
    analyze_parser.add_argument("--format", choices=['jtl', 'k6', 'gatling', 'locust'], help="Explicitly specify the file format (auto-detected by default)")
    analyze_parser.add_argument("--output", help="Path to save the generated analysis report (Markdown format)")
    analyze_parser.add_argument("--explain", action="store_true", help="Enable AI-powered Root Cause Analysis (requires API key or local LLM)")
    analyze_parser.add_argument("--prometheus-url", help="URL of the Prometheus server to fetch system metrics (e.g., http://localhost:9090)")
    analyze_parser.add_argument("--llm-url", help="Base URL for a custom/local LLM API (e.g., http://localhost:11434/v1 for Ollama)")
    analyze_parser.add_argument("--llm-model", help="Name of the LLM model to use (e.g., gpt-4, claude-3-opus, llama3)")

    args = parser.parse_args()

    if args.command == "analyze":
        try:
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

            print(f"Analyzing {args.file} ({file_format})...")
            df = file_parser.parse()
            stats = file_parser.get_summary_stats()

            print("\n--- Test Summary ---")
            print(f"Total Requests: {stats.get('total_requests')}")
            print(f"Avg Latency: {stats.get('avg_latency'):.2f} ms")
            print(f"P99 Latency: {stats.get('p99_latency'):.2f} ms")
            print(f"Error Rate: {stats.get('error_rate'):.2f}%")
            
            if df.empty:
                print("No data found.")
                return

            # 2. Detect Anomalies
            print("\n--- Detecting Anomalies ---")
            detector = AnomalyDetector(df)
            anomalies = detector.detect_latency_anomalies()
            anomaly_summary = detector.get_anomaly_summary(anomalies)
            
            print(f"Found {anomaly_summary['count']} latency anomalies.")
            if anomaly_summary['count'] > 0:
                print(f"Average Anomaly Latency: {anomaly_summary['avg_latency']:.2f} ms")
                print(f"Max Anomaly Latency: {anomaly_summary['max_latency']:.2f} ms")
                print("Anomaly Timestamps (first 5):")
                for ts in anomaly_summary['timestamps'][:5]:
                    print(f" - {ts}")

            # 3. Prometheus Metrics (Optional)
            prom_metrics = {}
            if args.prometheus_url:
                print("\n--- Fetching Prometheus Metrics ---")
                try:
                    prom = PrometheusClient(args.prometheus_url)
                    # Use a dummy time range for now, or infer from data
                    # For simplicity, we'll just fetch current metrics in this demo
                    prom_metrics = prom.get_system_metrics(stats['start_time'], stats['end_time'])
                    print(f"Fetched {len(prom_metrics)} metric types.")
                except Exception as e:
                    print(f"Warning: Failed to fetch Prometheus metrics: {e}")

            # 4. Explain (Optional)
            if args.explain:
                print("\n--- AI Analysis (Heimr) ---")
                
                # Determine provider
                provider = "mock"
                if args.llm_url or os.environ.get("OPENAI_API_KEY"):
                    provider = "openai"
                elif os.environ.get("ANTHROPIC_API_KEY"):
                    provider = "anthropic"
                
                print(f"Using LLM Provider: {provider.upper()}")
                
                llm = LLMClient(
                    provider=provider,
                    base_url=args.llm_url,
                    model=args.llm_model
                )
                # Pass prom_metrics to LLM (mock will ignore for now, but interface is ready)
                explanation = llm.generate_explanation(stats, anomaly_summary) 
                print(explanation)

                # Save report if requested
                if args.output:
                    with open(args.output, "w") as f:
                        f.write(explanation)
                    print(f"\n✅ Report saved to: {args.output}")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
