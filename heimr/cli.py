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


def enhance_llm_output(llm_text: str, result) -> str:
    """
    Enhance LLM output with inline visualizations based on detected keywords.
    
    Detects patterns like:
    - "correlation between X and Y" -> adds correlation badge
    - "spike at time T" -> adds timeline marker
    - "error log shows..." -> adds scrollable log box
    """
    import re
    
    if not llm_text:
        return llm_text
    
    enhanced = llm_text
    annotations = []
    
    # Detect correlation mentions
    correlation_patterns = [
        r'correlation between ([\w\s]+) and ([\w\s]+)',
        r'correlates with ([\w\s]+)',
        r'relationship between ([\w\s]+) and ([\w\s]+)',
        r'([\w\s]+) increased.*when ([\w\s]+)',
        r'([\w\s]+) spiked.*alongside ([\w\s]+)',
    ]
    
    correlations_found = []
    for pattern in correlation_patterns:
        matches = re.findall(pattern, enhanced, re.IGNORECASE)
        correlations_found.extend(matches)
    
    # Add correlation badge if correlations were mentioned
    if correlations_found:
        badge = "\n\n> 📊 **Correlations Detected**: "
        for corr in correlations_found[:3]:  # Max 3
            if isinstance(corr, tuple):
                badge += f"`{corr[0].strip()}` ↔ `{corr[1].strip()}`, "
            else:
                badge += f"`{corr.strip()}`, "
        badge = badge.rstrip(", ") + "\n"
        annotations.append(badge)
    
    # Detect spike mentions
    spike_patterns = [
        r'spike at (\d{1,2}:\d{2})',
        r'peaked at (\d{1,2}:\d{2})',
        r'surge at (\d{1,2}:\d{2})',
    ]
    
    spikes_found = []
    for pattern in spike_patterns:
        matches = re.findall(pattern, enhanced, re.IGNORECASE)
        spikes_found.extend(matches)
    
    if spikes_found:
        badge = "> ⏱️ **Key Timestamps**: "
        badge += ", ".join([f"`{t}`" for t in spikes_found[:5]])
        badge += "\n"
        annotations.append(badge)
    
    # Detect log/error references and create scrollable box
    if result.loki_logs and ('error log' in enhanced.lower() or 'logs show' in enhanced.lower()):
        # Add a sample of relevant logs in a scrollable box
        log_samples = result.loki_logs[:3]
        if log_samples:
            log_box = "\n\n<details>\n<summary>📜 Referenced Error Logs (click to expand)</summary>\n\n```\n"
            for log in log_samples:
                log_str = str(log)[:200]
                log_box += f"{log_str}\n"
            log_box += "```\n</details>\n"
            annotations.append(log_box)
    
    # Insert annotations at the end of the LLM output
    if annotations:
        enhanced += "\n\n---\n### 🔗 Analysis Insights\n"
        enhanced += "\n".join(annotations)
    
    return enhanced


def detect_timeline_mismatch(result) -> dict:
    """
    Detect if observability data timeline doesn't match the load test window.
    
    Returns dict with:
        - has_mismatch: bool
        - test_start/test_end: load test window
        - prom_start/prom_end: prometheus window (if available)
        - overlap_pct: percentage of overlap
        - message: human-readable warning
    """
    mismatch = {
        'has_mismatch': False,
        'test_start': None,
        'test_end': None,
        'prom_start': None,
        'prom_end': None,
        'overlap_pct': 100,
        'message': None
    }
    
    df = result.df
    if df.empty or 'timestamp_dt' not in df.columns:
        return mismatch
    
    # Get load test time window
    test_start = df['timestamp_dt'].min()
    test_end = df['timestamp_dt'].max()
    mismatch['test_start'] = test_start
    mismatch['test_end'] = test_end
    
    # Check Prometheus metrics timestamps
    if result.prom_metrics:
        try:
            from heimr.prometheus_normalizer import PrometheusNormalizer
            import pandas as pd
            
            prom_timestamps = []
            for metric_name, metric_data in result.prom_metrics.items():
                series = PrometheusNormalizer.extract_time_series(metric_data)
                for point in series:
                    prom_timestamps.append(point['timestamp'])
            
            if prom_timestamps:
                prom_start = pd.Timestamp(min(prom_timestamps), unit='s')
                prom_end = pd.Timestamp(max(prom_timestamps), unit='s')
                mismatch['prom_start'] = prom_start
                mismatch['prom_end'] = prom_end
                
                # Calculate overlap
                overlap_start = max(test_start, prom_start)
                overlap_end = min(test_end, prom_end)
                
                test_duration = (test_end - test_start).total_seconds()
                if test_duration > 0:
                    overlap_duration = max(0, (overlap_end - overlap_start).total_seconds())
                    overlap_pct = (overlap_duration / test_duration) * 100
                    mismatch['overlap_pct'] = overlap_pct
                    
                    if overlap_pct < 50:
                        mismatch['has_mismatch'] = True
                        mismatch['message'] = (
                            f"⚠️ **Timeline Mismatch**: Prometheus data covers only "
                            f"{overlap_pct:.0f}% of the load test window. "
                            f"Metrics may not reflect actual test conditions."
                        )
                    elif overlap_pct < 90:
                        mismatch['has_mismatch'] = True
                        mismatch['message'] = (
                            f"⚠️ **Partial Timeline Overlap**: {overlap_pct:.0f}% overlap "
                            f"between load test and Prometheus data."
                        )
        except Exception:
            pass  # Silently ignore parsing errors
    
    return mismatch


def generate_markdown_report_content(result: AnalysisResult, args) -> str:
    """Generates the full markdown report content with premium formatting."""
    df = result.df
    kpi_data = result.kpi
    
    # === SEMAPHORE STATUS LOGIC ===
    # 🟢 OK: No anomalies, no errors, no warnings
    # 🟡 WARNING: No anomalies BUT (Loki errors OR Tempo slow traces OR concerning metrics)
    # 🔴 FAILED: Anomalies detected OR high error rate
    
    has_anomalies = result.anomaly_summary.get('count', 0) > 0
    has_errors = kpi_data['errors']['rate'] > 0
    has_loki_errors = len(result.loki_logs) > 0
    has_slow_traces = len(result.tempo_traces) > 5  # More than 5 slow traces
    
    if has_anomalies or kpi_data['errors']['rate'] > 1.0:
        status = "FAILED"
        status_icon = "🔴"
        status_color = "#EF4444"
    elif has_loki_errors or has_slow_traces or has_errors:
        status = "WARNING"
        status_icon = "🟡"
        status_color = "#F59E0B"
    else:
        status = "OK"
        status_icon = "🟢"
        status_color = "#22C55E"
    
    # === EXECUTIVE SUMMARY ===
    report = ""
    
    # Header with status banner
    report += f"""
<div style="background: linear-gradient(135deg, {status_color}22, {status_color}11); border-left: 4px solid {status_color}; padding: 20px; margin-bottom: 20px; border-radius: 8px;">

# {status_icon} Performance Analysis: **{status}**

</div>

"""
    
    # One-liner verdict
    total_reqs = kpi_data['throughput']['total_requests']
    error_rate = kpi_data['errors']['rate']
    p99 = kpi_data['latency']['p99']
    duration = kpi_data['duration']
    
    verdict_parts = [f"Processed **{total_reqs:,} requests** in {duration:.0f}s"]
    if error_rate > 0:
        verdict_parts.append(f"with **{error_rate:.2f}%** errors")
    if p99 > 500:
        verdict_parts.append(f"P99 latency **{p99:.0f}ms** exceeds typical API threshold")
    
    report += f"> {' '.join(verdict_parts)}.\n\n"
    
    # Check for timeline mismatch warning
    timeline_info = detect_timeline_mismatch(result)
    if timeline_info['has_mismatch']:
        report += f"> {timeline_info['message']}\n\n"
    
    # Key Metrics Grid
    report += "## 📊 Key Metrics\n\n"
    report += "| Throughput | Error Rate | P99 Latency | Anomalies |\n"
    report += "|:---:|:---:|:---:|:---:|\n"
    anomaly_count = result.anomaly_summary.get('count', 0)
    report += f"| **{kpi_data['throughput']['requests_per_second']:.1f}** req/s | **{error_rate:.2f}%** | **{p99:.0f}** ms | **{anomaly_count}** |\n\n"
    
    # Top Recommendation (heuristic-based)
    if has_anomalies:
        # Find worst endpoint
        if not df.empty and 'endpoint' in df.columns:
            endpoint_p99 = df.groupby('endpoint')['elapsed'].quantile(0.99)
            worst = endpoint_p99.idxmax()
            report += f"> 💡 **Recommendation**: Investigate `{worst}` — P99 latency is {endpoint_p99[worst]:.0f}ms\n\n"
    elif has_loki_errors:
        report += f"> 💡 **Recommendation**: Review {len(result.loki_logs)} error logs in Loki for application issues\n\n"
    elif has_slow_traces:
        report += f"> 💡 **Recommendation**: Analyze {len(result.tempo_traces)} slow traces in Tempo for bottlenecks\n\n"
    
    # Context Tags
    if args.tag:
        report += "### Build Context\n"
        report += "| Key | Value |\n|---|---|\n"
        for tag in args.tag:
            if '=' in tag:
                k, v = tag.split('=', 1)
                report += f"| **{k}** | `{v}` |\n"
            else:
                report += f"| **Tag** | `{tag}` |\n"
        report += "\n"
    
    # === PERFORMANCE CHARTS ===
    report += "---\n\n## 📈 Performance Charts\n\n"
    
    try:
        from heimr.report_charts import ReportCharts
        
        # Latency Histogram
        latency_chart = ReportCharts.latency_histogram(df)
        if latency_chart:
            report += "### Response Time Distribution\n\n"
            report += latency_chart + "\n\n"
        
        # Response Time Over Time
        response_chart = ReportCharts.response_time_over_time(df)
        if response_chart:
            report += "### Response Time Over Load\n\n"
            report += response_chart + "\n\n"
        
        # Throughput
        throughput_chart = ReportCharts.throughput_over_time(df)
        if throughput_chart:
            report += "### Throughput Over Time\n\n"
            report += throughput_chart + "\n\n"
        
        # Error Rate with Throughput Overlay
        error_chart = ReportCharts.error_rate_with_throughput(df)
        if error_chart:
            report += "### Error Rate (with Throughput Overlay)\n\n"
            report += error_chart + "\n\n"
            
    except ImportError:
        report += "*Charts unavailable - install plotly: `pip install plotly kaleido`*\n\n"
    except Exception as e:
        report += f"*Chart generation error: {e}*\n\n"
    
    # === RESOURCE UTILIZATION ===
    report += "---\n\n## 🖥️ Resource Utilization\n\n"
    
    if result.prom_metrics:
        try:
            from heimr.report_charts import ReportCharts
            from heimr.prometheus_normalizer import PrometheusNormalizer
            
            categorized = PrometheusNormalizer.categorize_metrics(result.prom_metrics)
            charts_added = False
            
            # CPU
            if categorized.get('cpu'):
                cpu_chart = ReportCharts.resource_utilization(result.prom_metrics, 'cpu')
                if cpu_chart:
                    report += "### CPU Utilization\n\n"
                    report += cpu_chart + "\n\n"
                    charts_added = True
            
            # Memory
            if categorized.get('memory'):
                mem_chart = ReportCharts.resource_utilization(result.prom_metrics, 'memory')
                if mem_chart:
                    report += "### Memory Usage\n\n"
                    report += mem_chart + "\n\n"
                    charts_added = True
            
            # GPU
            if categorized.get('gpu'):
                gpu_chart = ReportCharts.resource_utilization(result.prom_metrics, 'gpu')
                if gpu_chart:
                    report += "### GPU Utilization\n\n"
                    report += gpu_chart + "\n\n"
                    charts_added = True
            
            # Disk I/O
            if categorized.get('disk'):
                disk_chart = ReportCharts.resource_utilization(result.prom_metrics, 'disk')
                if disk_chart:
                    report += "### Disk I/O\n\n"
                    report += disk_chart + "\n\n"
                    charts_added = True
            
            # Network I/O
            if categorized.get('network'):
                net_chart = ReportCharts.resource_utilization(result.prom_metrics, 'network')
                if net_chart:
                    report += "### Network I/O\n\n"
                    report += net_chart + "\n\n"
                    charts_added = True
            
            # Database
            if categorized.get('db'):
                db_chart = ReportCharts.resource_utilization(result.prom_metrics, 'db')
                if db_chart:
                    report += "### Database Metrics\n\n"
                    report += db_chart + "\n\n"
                    charts_added = True
            
            # Messaging/Streaming (Kafka, RabbitMQ, etc.)
            if categorized.get('messaging'):
                msg_chart = ReportCharts.resource_utilization(result.prom_metrics, 'messaging')
                if msg_chart:
                    report += "### Messaging/Streaming\n\n"
                    report += msg_chart + "\n\n"
                    charts_added = True
            
            # HTTP/Application Metrics
            if categorized.get('http'):
                http_chart = ReportCharts.resource_utilization(result.prom_metrics, 'http')
                if http_chart:
                    report += "### HTTP/Application Metrics\n\n"
                    report += http_chart + "\n\n"
                    charts_added = True
            
            if not charts_added:
                report += "> ⚠️ *Prometheus metrics received but no recognizable CPU/Memory/GPU patterns found.*\n\n"
                    
        except Exception as e:
            report += f"*Resource charts error: {e}*\n\n"
    else:
        report += """> ⚠️ **No Prometheus metrics provided.**
>
> Add `--prometheus <url_or_file>` to include hardware monitoring:
> - CPU/Memory utilization
> - GPU metrics (if available)
> - Disk and Network I/O

"""
    
    # === DETAILED DATA BREAKDOWN ===
    report += "---\n\n## 📋 Detailed Data Breakdown\n\n"
    
    # Per Endpoint KPIs
    report += "### Per-Endpoint Performance\n\n"
    report += "| Endpoint | Requests | RPS | Error % | Avg (ms) | P95 (ms) | P99 (ms) |\n"
    report += "|---|---:|---:|---:|---:|---:|---:|\n"
    
    if not df.empty and 'endpoint' in df.columns:
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
            
            # Color coding for error rate
            error_display = f"{error_rate:.2f}%"
            if error_rate > 1:
                error_display = f"**{error_rate:.2f}%** 🔴"
            elif error_rate > 0:
                error_display = f"{error_rate:.2f}% 🟡"
                
            report += f"| `{name}` | {count:,} | {throughput:.1f} | {error_display} | {avg:.0f} | {p95:.0f} | {p99:.0f} |\n"
        
        # Total row
        report += f"| **TOTAL** | **{kpi_data['throughput']['total_requests']:,}** | "
        report += f"**{kpi_data['throughput']['requests_per_second']:.1f}** | "
        report += f"**{kpi_data['errors']['rate']:.2f}%** | "
        report += f"**{kpi_data['latency']['avg']:.0f}** | "
        report += f"**{kpi_data['latency']['p95']:.0f}** | "
        report += f"**{kpi_data['latency']['p99']:.0f}** |\n"
    else:
        report += "| *No endpoint data* | - | - | - | - | - | - |\n"
    
    report += "\n"
    
    # Loki Logs Summary (Grouped by Error Type)
    report += "### 📝 Log Analysis (Loki)\n\n"
    
    if result.loki_logs:
        # Group by error type/pattern
        error_groups = {}
        for log in result.loki_logs:
            log_str = str(log).lower()
            # Simple grouping by first significant words
            if 'error' in log_str:
                key = 'ERROR'
            elif 'warn' in log_str:
                key = 'WARNING'
            elif 'timeout' in log_str:
                key = 'TIMEOUT'
            elif 'exception' in log_str:
                key = 'EXCEPTION'
            else:
                key = 'OTHER'
            
            if key not in error_groups:
                error_groups[key] = {'count': 0, 'samples': []}
            error_groups[key]['count'] += 1
            if len(error_groups[key]['samples']) < 2:
                error_groups[key]['samples'].append(log[:150] + '...' if len(str(log)) > 150 else log)
        
        report += "| Type | Count | Sample |\n|---|---:|---|\n"
        for error_type, data in sorted(error_groups.items(), key=lambda x: -x[1]['count']):
            sample = data['samples'][0] if data['samples'] else '-'
            report += f"| **{error_type}** | {data['count']} | `{sample}` |\n"
        report += "\n"
    else:
        report += """> ℹ️ **No Loki logs provided.**
>
> Add `--loki <url_or_file>` to include application log analysis:
> - Error log grouping by type
> - Warning detection
> - Exception stack traces

"""
    
    # Tempo Traces Summary
    report += "### 🔍 Slow Traces (Tempo)\n\n"
    
    if result.tempo_traces:
        report += "| Trace ID | Duration | Operation | Status |\n|---|---:|---|---|\n"
        
        for trace in result.tempo_traces[:10]:
            trace_id = trace.get('traceID', 'N/A')[:16] + '...'
            duration = trace.get('duration', 0)
            
            # Extract root span info
            spans = trace.get('spans', [])
            root_op = 'Unknown'
            status = 'OK'
            if spans:
                root_span = spans[0]
                root_op = root_span.get('operationName', 'Unknown')
                # Check for error tags
                for tag in root_span.get('tags', []):
                    if tag.get('key') == 'error' and tag.get('value'):
                        status = '🔴 Error'
                    elif tag.get('key') == 'http.status_code':
                        code = int(tag.get('value', 200))
                        if code >= 500:
                            status = f'🔴 {code}'
                        elif code >= 400:
                            status = f'🟡 {code}'
            
            report += f"| `{trace_id}` | {duration:.0f}ms | `{root_op}` | {status} |\n"
        
        if len(result.tempo_traces) > 10:
            report += f"\n*... and {len(result.tempo_traces) - 10} more slow traces*\n"
        report += "\n"
    else:
        report += """> ℹ️ **No Tempo traces provided.**
>
> Add `--tempo <url_or_file>` to include distributed trace analysis:
> - Slow request breakdown
> - Service-to-service latency
> - Error propagation paths

"""
    
    # === AI ROOT CAUSE ANALYSIS ===
    report += "---\n\n## 🤖 AI Root Cause Analysis\n\n"
    
    if result.llm_explanation:
        # Enhance LLM output with inline visualizations
        enhanced_analysis = enhance_llm_output(result.llm_explanation, result)
        report += enhanced_analysis
        report += "\n"
    else:
        report += """> ℹ️ **AI analysis not available.**
>
> Run without `--no-llm` to enable AI-powered root cause analysis.
> Requires Ollama with Llama 3.1 or an OpenAI API key.
>
> Quick setup: `heimr setup-llm`

"""
    
    return report


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
    analyze_parser.add_argument("--fail-on-regression", type=float, help="Fail if metric worsens by %%")
    analyze_parser.add_argument("--fail-condition", action="append", help="Fail if condition is met")
    analyze_parser.add_argument("--tag", action="append", help="Add metadata tag to report")
    analyze_parser.add_argument("--ci-summary", nargs="?", const="GITHUB_STEP_SUMMARY", help="Generate GH Summary")
    analyze_parser.add_argument("--junit-output", help="Path to save JUnit XML report")

    args = parser.parse_args()

    if args.command == "config-init":
        config_content = '''# Heimr Configuration File
# Documentation: https://github.com/jdestevezcastillo-perfeng/Heimr.ai/wiki

# === Load Test Analysis ===
# Enable AI-powered root cause analysis
disable_llm: false

# LLM Configuration
# Use local Ollama models or remote providers
llm_model: qwen2.5:14b  # Recommended for best performance/speed balance
llm_url: http://localhost:11434  # Default Ollama URL

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
            # Step 1: Generate HTML report with interactive Plotly charts
            print("\n--- Generating HTML Report (Interactive Charts) ---")
            try:
                from heimr.report_charts import ReportCharts
                from heimr.html_generator import HTMLReportGenerator
                
                # Use HTML mode for interactive charts
                ReportCharts.set_output_mode('html')
                html_content = generate_markdown_report_content(result, args)
                
                html_gen = HTMLReportGenerator()
                html_path = args.output.rsplit('.', 1)[0] + '.html'
                html_gen.generate_html(html_content, html_path)
                print(f"✅ HTML report saved to: {html_path}")
                print("   💡 Open in browser and press Ctrl+P to save as PDF")
            except Exception as e:
                print(f"Warning: Failed to generate HTML: {e}")
                import traceback
                traceback.print_exc()
            
            # Step 2: Generate Markdown report with static PNG charts (for GitHub/GitLab)
            print("\n--- Generating Markdown Report (Static Charts) ---")
            try:
                from heimr.report_charts import ReportCharts
                
                # Switch to image mode for static PNG charts
                ReportCharts.set_output_mode('image')
                md_content = generate_markdown_report_content(result, args)
                
                with open(args.output, "w") as f:
                    f.write(md_content)
                print(f"✅ Markdown report saved to: {args.output}")
                
                # Reset to HTML mode
                ReportCharts.set_output_mode('html')
            except Exception as e:
                print(f"Warning: Failed to generate Markdown with images: {e}")
                # Fallback: save with HTML charts (may not render in GitHub)
                from heimr.report_charts import ReportCharts
                ReportCharts.set_output_mode('html')
                fallback_content = generate_markdown_report_content(result, args)
                with open(args.output, "w") as f:
                    f.write(fallback_content)
                print(f"⚠️ Saved Markdown with HTML charts (install kaleido for static images)")

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
