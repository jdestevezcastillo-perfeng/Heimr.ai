# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import argparse
import sys
import os
import yaml
from heimr.analyzer import AnalysisResult
from heimr.setup_llm import setup_llm

# Extracted helpers (P2.3 refactor). Kept re-exported here for compatibility.
from heimr.commands.config import load_config as _load_config_mod, normalize_config as _normalize_config_mod, merge_config_with_args as _merge_config_mod
from heimr.reporting.markdown import (
    enhance_llm_output as _enhance_llm_output_mod,
    create_correlation_chart as _create_correlation_chart_mod,
    detect_timeline_mismatch as _detect_timeline_mismatch_mod,
    extract_llm_tldr as _extract_llm_tldr_mod,
)


def load_config(config_path: str) -> dict:
    """
    Load configuration from a YAML file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    return normalize_config(config)


def normalize_config(config: dict) -> dict:
    """
    Normalize legacy/alias keys to the canonical config schema.

    Canonical keys:
      - llm_url, llm_model, disable_llm
      - prometheus, loki, tempo, prompt_template, output, compare_*

    Legacy/aliases supported:
      - explain: false => disable_llm: true
      - no_llm: true => disable_llm: true
      - llm_url without /v1 => append /v1 for Ollama/OpenAI-compatible servers
    """
    if not isinstance(config, dict):
        return {}

    normalized = dict(config)

    # Legacy boolean flags
    if normalized.get("disable_llm") is None:
        if normalized.get("no_llm") is True:
            normalized["disable_llm"] = True
        elif normalized.get("explain") is False:
            normalized["disable_llm"] = True
        else:
            normalized["disable_llm"] = False

    # Keep explain key for backward compatibility but don't use it later

    llm_url = normalized.get("llm_url")
    if isinstance(llm_url, str) and llm_url.startswith("http"):
        # If URL ends at port or base, add /v1 to match OpenAI-compatible paths.
        if not llm_url.rstrip("/").endswith("/v1"):
            normalized["llm_url"] = llm_url.rstrip("/") + "/v1"

    return normalized


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
        'disable_llm': 'no_llm',
        'no_llm': 'no_llm',
        'prompt_template': 'prompt_template',
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
    - "correlation between X and Y" -> adds correlation chart
    - "spike at time T" -> adds timeline marker
    - "error log shows..." -> adds scrollable log box
    """
    import re
    from heimr.reporting.charts import ReportCharts
    
    if not llm_text:
        return llm_text
    
    enhanced = llm_text
    annotations = []
    
    # Detect correlation mentions and generate charts
    correlation_patterns = [
        r'correlation between ([\w\s]+) and ([\w\s]+)',
        r'relationship between ([\w\s]+) and ([\w\s]+)',
        r'([\w\s]+) increased.*when ([\w\s]+)',
        r'([\w\s]+) spiked.*alongside ([\w\s]+)',
    ]
    
    correlations_found = []
    for pattern in correlation_patterns:
        matches = re.findall(pattern, enhanced, re.IGNORECASE)
        correlations_found.extend(matches)
    
    # Generate correlation charts if we have the data
    if correlations_found and result.df is not None and not result.df.empty:
        for idx, corr in enumerate(correlations_found[:2]):  # Max 2 charts
            if isinstance(corr, tuple) and len(corr) == 2:
                metric1 = corr[0].strip().lower()
                metric2 = corr[1].strip().lower()
                
                # Try to match to actual columns/metrics
                # Common mappings
                metric_map = {
                    'latency': 'elapsed',
                    'response time': 'elapsed',
                    'cpu': 'cpu_usage',
                    'memory': 'memory_usage',
                    'throughput': 'requests',
                    'load': 'vus',
                }
                
                col1 = metric_map.get(metric1, metric1)
                col2 = metric_map.get(metric2, metric2)
                
                # Check if we can create a time-series correlation chart
                if 'timestamp_dt' in result.df.columns:
                    try:
                        # Create dual-axis chart
                        chart_html = create_correlation_chart(result.df, col1, col2, metric1, metric2)
                        if chart_html:
                            annotations.append(f"\n\n{chart_html}\n\n")
                    except Exception:
                        pass  # Silently skip if chart generation fails
    
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


def create_correlation_chart(df, col1, col2, label1, label2):
    """Create a dual-axis correlation chart between two metrics."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import pandas as pd
        
        # Prepare data - resample to reduce points
        df_sorted = df.sort_values('timestamp_dt')
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('30s')
        
        # Try to aggregate the metrics
        agg_dict = {}
        if col1 in df_sorted.columns or col1 == 'elapsed':
            agg_dict[col1 if col1 in df_sorted.columns else 'elapsed'] = 'mean'
        if col2 in df_sorted.columns or col2 == 'elapsed':
            agg_dict[col2 if col2 in df_sorted.columns else 'elapsed'] = 'mean'
        
        if not agg_dict:
            return None
        
        agg = df_sorted.groupby('time_bucket').agg(agg_dict).reset_index()
        
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add traces
        actual_col1 = col1 if col1 in agg.columns else 'elapsed'
        actual_col2 = col2 if col2 in agg.columns else 'elapsed'
        
        if actual_col1 in agg.columns:
            fig.add_trace(
                go.Scatter(x=agg['time_bucket'], y=agg[actual_col1],
                          name=label1.title(), line=dict(color='#00d9ff', width=2)),
                secondary_y=False,
            )
        
        if actual_col2 in agg.columns and actual_col1 != actual_col2:
            fig.add_trace(
                go.Scatter(x=agg['time_bucket'], y=agg[actual_col2],
                          name=label2.title(), line=dict(color='#00ffa3', width=2)),
                secondary_y=True,
            )
        
        # Update layout
        fig.update_layout(
            title=f"Correlation: {label1.title()} vs {label2.title()}",
            paper_bgcolor='#0a192f',
            plot_bgcolor='#0a192f',
            font=dict(color='#e6f1ff'),
            height=400,
            hovermode='x unified'
        )
        
        fig.update_xaxes(title_text="Time", gridcolor='rgba(255,255,255,0.1)')
        fig.update_yaxes(title_text=label1.title(), secondary_y=False, gridcolor='rgba(255,255,255,0.1)')
        fig.update_yaxes(title_text=label2.title(), secondary_y=True, gridcolor='rgba(255,255,255,0.05)')
        
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    except Exception:
        return None


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


def extract_llm_tldr(llm_text: str, llm_client=None) -> dict:
    """
    Extract a TLDR summary from LLM analysis output using another LLM call.
    Returns dict with 'root_cause' and 'fix' keys.
    """
    import re
    
    tldr = {'root_cause': None, 'fix': None}
    
    # If we have an LLM client, use it to generate TLDR
    if llm_client:
        try:
            prompt = f"""Summarize this performance analysis in exactly 2 lines:

Line 1 - Root cause (one complete sentence, 100-120 chars): What caused the performance issue?
Line 2 - Fix (one complete sentence, 100-120 chars): What's the best solution?

Analysis:
{llm_text[:2000]}

Format your response EXACTLY like this (no extra text):
ROOT_CAUSE: [your sentence]
FIX: [your sentence]"""
            
            # Determine model to use (with defaults)
            if llm_client.provider == 'openai':
                model = llm_client.model or "gpt-4"
                import openai
                client = openai.OpenAI(base_url=llm_client.base_url, api_key=llm_client.api_key or "dummy")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=250
                )
                result = response.choices[0].message.content
            elif llm_client.provider == 'anthropic':
                model = llm_client.model or "claude-3-sonnet-20240229"
                import anthropic
                client = anthropic.Anthropic(api_key=llm_client.api_key)
                response = client.messages.create(
                    model=model,
                    max_tokens=250,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text
            else:  # local/ollama
                model = llm_client.model or "qwen3.5:9b"
                import openai
                client = openai.OpenAI(base_url=llm_client.base_url, api_key="ollama")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=250
                )
                result = response.choices[0].message.content
            
            # Parse response
            root_match = re.search(r'ROOT_CAUSE:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
            fix_match = re.search(r'FIX:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
            
            if root_match:
                tldr['root_cause'] = root_match.group(1).strip()[:250]
            if fix_match:
                tldr['fix'] = fix_match.group(1).strip()[:250]
            
            # If parsing failed, show what we got
            if not tldr['root_cause'] or not tldr['fix']:
                print(f"⚠️  TLDR LLM returned unexpected format. Response: {result[:200]}")
                tldr['root_cause'] = "⚠️ TLDR generation failed - LLM response format error"
                tldr['fix'] = "⚠️ See detailed analysis below"
                
        except Exception as e:
            # Show clear error message instead of confusing regex fallback
            print(f"⚠️  TLDR LLM call failed: {e}")
            tldr['root_cause'] = "⚠️ TLDR generation failed - LLM error"
            tldr['fix'] = "⚠️ See detailed analysis below"
    else:
        # No LLM client available
        tldr['root_cause'] = "⚠️ TLDR unavailable - no LLM configured"
        tldr['fix'] = "⚠️ See detailed analysis below"
    
    return tldr


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
    
    # === METADATA SECTION ===
    import os
    from datetime import datetime
    
    # Get file name from args
    test_file = os.path.basename(args.file) if hasattr(args, 'file') else 'Unknown'
    
    # Get test period from dataframe
    test_start = df['timestamp_dt'].min() if not df.empty and 'timestamp_dt' in df.columns else None
    test_end = df['timestamp_dt'].max() if not df.empty and 'timestamp_dt' in df.columns else None
    
    report += """<div style="background: #0a192f; border: 1px solid #00d9ff33; padding: 15px; margin-bottom: 20px; border-radius: 6px; font-size: 13px;">

### 📊 Report Metadata

"""
    
    report += f"**Load Test File:** `{test_file}`\n\n"
    
    if test_start and test_end:
        test_duration = (test_end - test_start).total_seconds()
        report += f"**Test Period:** {test_start.strftime('%Y-%m-%d %H:%M:%S')} → {test_end.strftime('%H:%M:%S')} ({test_duration/60:.1f} minutes)\n\n"

    # Optional Grafana dashboard link scoped to test window
    grafana_url = getattr(args, "grafana_url", None)
    grafana_uid = getattr(args, "grafana_dashboard_uid", None)
    if grafana_url and grafana_uid and test_start and test_end:
        from urllib.parse import quote
        base = grafana_url.rstrip("/")
        frm = int(test_start.timestamp() * 1000)
        to = int(test_end.timestamp() * 1000)
        dash_url = f"{base}/d/{quote(grafana_uid)}?from={frm}&to={to}"
        report += f"**Grafana Dashboard:** {dash_url}\n\n"
    
    # Show observability data periods if available
    if result.prom_metrics:
        # Extract time range from Prometheus data
        prom_times = []
        for metric_name, metric_data in result.prom_metrics.items():
            if isinstance(metric_data, dict) and 'data' in metric_data:
                if 'result' in metric_data['data']:
                    for series in metric_data['data']['result']:
                        if 'values' in series:
                            prom_times.extend([v[0] for v in series['values']])
        if prom_times:
            prom_start = datetime.fromtimestamp(min(prom_times))
            prom_end = datetime.fromtimestamp(max(prom_times))
            report += f"**Prometheus Data:** {prom_start.strftime('%Y-%m-%d %H:%M:%S')} → {prom_end.strftime('%H:%M:%S')}\n\n"
    
    if result.loki_logs:
        report += f"**Loki Logs:** {len(result.loki_logs)} log entries collected\n\n"
    
    if result.tempo_traces:
        report += f"**Tempo Traces:** {len(result.tempo_traces)} slow traces collected\n\n"
    
    report += "</div>\n\n"
    
    # Header with visual semaphore status
    report += f"""
<div style="background: linear-gradient(135deg, {status_color}22, {status_color}11); border-left: 4px solid {status_color}; padding: 20px; margin-bottom: 20px; border-radius: 8px;">

# Performance Analysis

<div style="display: flex; align-items: center; gap: 15px; margin-top: 15px;">
  <div style="display: flex; gap: 10px; align-items: center;">
    <span style="font-size: 32px; opacity: {'1.0' if status == 'OK' else '0.3'};">🟢</span>
    <span style="font-size: 32px; opacity: {'1.0' if status == 'WARNING' else '0.3'};">🟡</span>
    <span style="font-size: 32px; opacity: {'1.0' if status == 'FAILED' else '0.3'};">🔴</span>
  </div>
  <div style="font-size: 24px; font-weight: bold; color: {status_color};">{status}</div>
</div>

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
    report += "| Total Reqs | Throughput | Avg | P50 | P95 | P99 | Max | Error Rate | Anomalies |\n"
    report += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
    
    anomaly_count = result.anomaly_summary.get('count', 0)
    total_reqs = kpi_data['throughput']['total_requests']
    rps = kpi_data['throughput']['requests_per_second']
    
    # Latency metrics
    l = kpi_data['latency']
    p50 = l.get('p50', 0) # Use get safely
    p95 = l.get('p95', 0)
    p99 = l.get('p99', 0)
    avg = l.get('avg', 0)
    max_lat = l.get('max', 0)
    
    report += f"| **{total_reqs:,}** | **{rps:.1f}** req/s | **{avg:.0f}** ms | **{p50:.0f}** ms | **{p95:.0f}** ms | **{p99:.0f}** ms | **{max_lat:.0f}** ms | **{error_rate:.2f}%** | **{anomaly_count}** |\n\n"

    # Per-endpoint KPI table (top 10 by p99)
    per_endpoint = kpi_data.get("per_endpoint", {})
    if per_endpoint:
        report += "## 🔎 Per-Endpoint KPIs (Top 10 by P99)\n\n"
        report += "| Endpoint | Requests | RPS | Error % | P50 | P95 | P99 |\n"
        report += "|---|---:|---:|---:|---:|---:|---:|\n"
        ranked = sorted(
            per_endpoint.items(),
            key=lambda kv: kv[1].get("latency", {}).get("p99", 0),
            reverse=True
        )[:10]
        for name, data in ranked:
            lat = data.get("latency", {})
            report += (
                f"| `{name}` | {data.get('total_requests', 0)} | {data.get('throughput_rps', 0):.2f} | "
                f"{data.get('error_rate', 0):.2f}% | {lat.get('p50', 0):.0f} | "
                f"{lat.get('p95', 0):.0f} | {lat.get('p99', 0):.0f} |\n"
            )
        report += "\n"
    
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
    
    # === TLDR SECTION ===
    if result.llm_explanation:
        # Extract TLDR using LLM
        tldr = extract_llm_tldr(result.llm_explanation, result.llm_client)
        
        if tldr['root_cause'] or tldr['fix']:
            report += """<div style="background: linear-gradient(135deg, #00d9ff22, #00ffa311); border-left: 4px solid #00d9ff; padding: 20px; margin-bottom: 25px; border-radius: 8px;">

<h3>⚡ TL;DR</h3>

"""
            if tldr['root_cause']:
                report += f"<p><strong>🔍 Find the Root:</strong><br>{tldr['root_cause']}</p>\n\n"
            
            if tldr['fix']:
                report += f"<p><strong>🔧 Fix the Cause:</strong><br>{tldr['fix']}</p>\n\n"
            
            report += "</div>\n\n"

    # === PERFORMANCE CHARTS ===
    report += "---\n\n## 📈 Performance Charts\n\n"
    
    try:
        from heimr.reporting.charts import ReportCharts
        
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
        
        # Response Time by Endpoint
        endpoint_chart = ReportCharts.response_time_by_endpoint(df)
        if endpoint_chart:
            report += "### Response Time by Endpoint\n\n"
            report += endpoint_chart + "\n\n"
        
        # Throughput by Endpoint
        throughput_endpoint_chart = ReportCharts.throughput_by_endpoint(df)
        if throughput_endpoint_chart:
            report += "### Throughput by Endpoint\n\n"
            report += throughput_endpoint_chart + "\n\n"
        

        
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
            from heimr.reporting.charts import ReportCharts
            from heimr.prometheus_normalizer import PrometheusNormalizer
            
            categorized = PrometheusNormalizer.categorize_metrics(result.prom_metrics)
            charts_added = False
            
            # Prepare Throughput Data for Overlay
            throughput_df = None
            if not df.empty and 'timestamp_dt' in df.columns:
                try:
                    df_sorted = df.sort_values('timestamp_dt')
                    df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
                    agg = df_sorted.groupby('time_bucket').size().reset_index(name='requests')
                    agg['rps'] = agg['requests'] / 10
                    # Standardize column names for ReportCharts
                    throughput_df = agg[['time_bucket', 'rps']].rename(columns={'time_bucket': 'time'})
                except Exception:
                    pass # Silently fail, just won't show overlay
            
            # CPU
            if categorized.get('cpu'):
                cpu_chart = ReportCharts.resource_utilization(result.prom_metrics, 'cpu', throughput_df)
                if cpu_chart:
                    report += "### CPU Utilization\n\n"
                    report += cpu_chart + "\n\n"
                    charts_added = True
            
            # Memory
            if categorized.get('memory'):
                mem_chart = ReportCharts.resource_utilization(result.prom_metrics, 'memory', throughput_df)
                if mem_chart:
                    report += "### Memory Usage\n\n"
                    report += mem_chart + "\n\n"
                    charts_added = True
            
            # GPU
            if categorized.get('gpu'):
                gpu_chart = ReportCharts.resource_utilization(result.prom_metrics, 'gpu', throughput_df)
                if gpu_chart:
                    report += "### GPU Utilization\n\n"
                    report += gpu_chart + "\n\n"
                    charts_added = True
            
            # Disk I/O
            if categorized.get('disk'):
                disk_chart = ReportCharts.resource_utilization(result.prom_metrics, 'disk', throughput_df)
                if disk_chart:
                    report += "### Disk I/O\n\n"
                    report += disk_chart + "\n\n"
                    charts_added = True
            
            # Network I/O
            if categorized.get('network'):
                net_chart = ReportCharts.resource_utilization(result.prom_metrics, 'network', throughput_df)
                if net_chart:
                    report += "### Network I/O\n\n"
                    report += net_chart + "\n\n"
                    charts_added = True
            
            # Database
            if categorized.get('db'):
                db_chart = ReportCharts.resource_utilization(result.prom_metrics, 'db', throughput_df)
                if db_chart:
                    report += "### Database Metrics\n\n"
                    report += db_chart + "\n\n"
                    charts_added = True
            
            # Messaging/Streaming (Kafka, RabbitMQ, etc.)
            if categorized.get('messaging'):
                msg_chart = ReportCharts.resource_utilization(result.prom_metrics, 'messaging', throughput_df)
                if msg_chart:
                    report += "### Messaging/Streaming\n\n"
                    report += msg_chart + "\n\n"
                    charts_added = True
            
            # HTTP/Application Metrics
            if categorized.get('http'):
                http_chart = ReportCharts.resource_utilization(result.prom_metrics, 'http', throughput_df)
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
    
    # === JVM ANALYSIS ===
    if result.jvm_thread_dump or result.jvm_heap_dump or result.jvm_gc_log:
        report += "---\n\n## ☕ JVM Analysis\n\n"
        
        try:
            from heimr.reporting.charts import ReportCharts
            
            # Thread State Pie Chart
            if result.jvm_thread_dump:
                thread_chart = ReportCharts.thread_state_pie(result.jvm_thread_dump)
                if thread_chart:
                    report += "### Thread States\n\n"
                    report += thread_chart + "\n\n"
                
                # Thread dump text summary
                summary = result.jvm_thread_dump.get('summary', {})
                if summary.get('has_deadlocks'):
                    report += f"> ⚠️ **DEADLOCK DETECTED:** {summary.get('deadlock_count', 0)} deadlock(s) found!\n\n"
                
                hot_locks = result.jvm_thread_dump.get('hot_locks', [])
                if hot_locks:
                    report += "**Lock Contention:**\n\n"
                    report += "| Lock | Waiters | Owner |\n"
                    report += "|---|:---:|---|\n"
                    for lock in hot_locks[:5]:
                        report += f"| `{lock.get('lock', 'unknown')[:20]}...` | {lock.get('waiter_count', 0)} | {lock.get('owner', 'unknown')} |\n"
                    report += "\n"
            
            # GC Pause Timeline
            if result.jvm_gc_log:
                gc_chart = ReportCharts.gc_pause_timeline(result.jvm_gc_log)
                if gc_chart:
                    report += "### GC Pause Timeline\n\n"
                    report += gc_chart + "\n\n"
                
                # GC summary stats
                gc_summary = result.jvm_gc_log.get('summary', {})
                report += f"**GC Summary:** {gc_summary.get('gc_type', 'Unknown')} collector, "
                report += f"{gc_summary.get('total_events', 0)} events, "
                report += f"{gc_summary.get('total_pause_seconds', 0):.2f}s total pause time\n\n"
                
                if gc_summary.get('full_gc_count', 0) > 0:
                    report += f"> ⚠️ **Warning:** {gc_summary.get('full_gc_count', 0)} Full GC events detected\n\n"
            
            # Heap dump summary (no chart, just stats)
            if result.jvm_heap_dump:
                heap_summary = result.jvm_heap_dump.get('heap_summary', {})
                report += "### Heap Analysis\n\n"
                report += f"**Total Heap:** {heap_summary.get('total_bytes_mb', 0):.1f} MB | "
                report += f"**Instances:** {heap_summary.get('total_instances', 0):,}\n\n"
                
                # Top classes table
                top_classes = result.jvm_heap_dump.get('top_classes', [])[:5]
                if top_classes:
                    report += "| Class | Size (MB) | Instances |\n"
                    report += "|---|---:|---:|\n"
                    for cls in top_classes:
                        class_name = cls.get('class_name', 'unknown')
                        if len(class_name) > 40:
                            class_name = "..." + class_name[-37:]
                        report += f"| `{class_name}` | {cls.get('bytes_mb', 0):.1f} | {cls.get('instances', 0):,} |\n"
                    report += "\n"
                
                # Potential leaks
                leaks = result.jvm_heap_dump.get('potential_leaks', [])
                if leaks:
                    report += "> ⚠️ **Potential Memory Leaks:**\n"
                    for leak in leaks[:3]:
                        report += f"> - `{leak.get('class_name', 'unknown')}`: {leak.get('reason', 'high instance count')}\n"
                    report += "\n"
                    
        except Exception as e:
            report += f"*JVM chart generation error: {e}*\n\n"
    
    # === DETAILED DATA BREAKDOWN ===
    report += "---\n\n## 📋 Detailed Data Breakdown\n\n"
    
    # Per Endpoint KPIs
    report += "### Per-Endpoint Performance\n\n"
    report += "| Endpoint | Requests | RPS | Error % | Avg (ms) | P95 (ms) | P99 (ms) | Max (ms) |\n"
    report += "|---|---:|---:|---:|---:|---:|---:|---:|\n"
    
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
                
            max_latency = group['elapsed'].max()
            report += f"| `{name}` | {count:,} | {throughput:.1f} | {error_display} | {avg:.2f} | {p95:.2f} | {p99:.2f} | {max_latency:.2f} |\n"
        
        # Total row
        report += f"| **TOTAL** | **{kpi_data['throughput']['total_requests']:,}** | "
        report += f"**{kpi_data['throughput']['requests_per_second']:.1f}** | "
        report += f"**{kpi_data['errors']['rate']:.2f}%** | "
        report += f"**{kpi_data['latency']['avg']:.2f}** | "
        report += f"**{kpi_data['latency']['p95']:.2f}** | "
        report += f"**{kpi_data['latency']['p99']:.2f}** | "
        report += f"**{kpi_data['latency']['max']:.2f}** |\n"
    else:
        report += "| *No endpoint data* | - | - | - | - | - | - |\n"
    
    report += "\n"
    
    # Loki Logs Summary (Grouped by Error Type with Collapsible Details)
    report += "### 📝 Log Analysis (Loki)\n\n"
    
    if result.loki_logs:
        # Group by error type and extract unique error patterns
        error_groups = {}
        for idx, log in enumerate(result.loki_logs):
            log_str = str(log).lower()
            
            # Classify by error type
            if 'error' in log_str:
                error_type = 'ERROR'
            elif 'warn' in log_str:
                error_type = 'WARNING'
            elif 'timeout' in log_str:
                error_type = 'TIMEOUT'
            elif 'exception' in log_str:
                error_type = 'EXCEPTION'
            else:
                error_type = 'OTHER'
            
            # Extract error pattern - try to find msg= field for better grouping
            # This helps group similar errors together even if timestamps differ
            import re
            error_signature = None
            
            # Try to extract msg="..." or err="..." field
            msg_match = re.search(r'msg="([^"]+)"', str(log))
            if msg_match:
                error_signature = msg_match.group(1)
            else:
                # Try err= field
                err_match = re.search(r'err="([^"]+)"', str(log))
                if err_match:
                    error_signature = err_match.group(1)
                else:
                    # Fallback: use first 100 chars (excluding timestamp)
                    # Remove common timestamp patterns
                    log_without_ts = re.sub(r'ts=\d{4}-\d{2}-\d{2}T[\d:\.]+Z?\s*', '', str(log))
                    error_signature = log_without_ts[:100].strip()
            
            if not error_signature:
                error_signature = str(log)[:100].strip()
            
            if error_type not in error_groups:
                error_groups[error_type] = {'count': 0, 'patterns': {}}
            
            error_groups[error_type]['count'] += 1
            
            # Track unique patterns
            if error_signature not in error_groups[error_type]['patterns']:
                error_groups[error_type]['patterns'][error_signature] = {
                    'count': 0,
                    'sample': log
                }
            error_groups[error_type]['patterns'][error_signature]['count'] += 1
        
        # Display collapsible sections for each error type
        for error_type, data in sorted(error_groups.items(), key=lambda x: -x[1]['count']):
            color = '#EF4444' if error_type == 'ERROR' else '#F59E0B' if error_type == 'WARNING' else '#6B7280'
            
            report += f"""<details style="margin-bottom: 15px; border: 1px solid {color}; border-radius: 6px; padding: 10px;">
<summary style="cursor: pointer; font-weight: bold; color: {color};">
{error_type} ({data['count']} occurrences, {len(data['patterns'])} unique patterns) - Click to expand
</summary>

"""
            # Show one sample per unique pattern
            for pattern_sig, pattern_data in sorted(data['patterns'].items(), key=lambda x: -x[1]['count'])[:10]:
                log_text = str(pattern_data['sample']).replace('`', '\\`')  # Escape backticks
                count = pattern_data['count']
                
                report += f"""<div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px; font-family: monospace; font-size: 12px; position: relative;">
<button onclick="navigator.clipboard.writeText(this.parentElement.querySelector('pre').textContent)" style="position: absolute; right: 10px; top: 10px; padding: 4px 8px; background: #00d9ff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;">📋 Copy</button>
<div style="margin-bottom: 5px; font-size: 11px; color: #666;">Occurred {count} time{'s' if count > 1 else ''}</div>
<pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word; color: #1a1a1a;">{log_text}</pre>
</div>

"""
            
            if len(data['patterns']) > 10:
                report += f"*... and {len(data['patterns']) - 10} more unique {error_type} patterns*\n\n"
            
            report += "</details>\n\n"
        
        report += "\n"
    else:
        report += """> ℹ️ **No Loki logs provided.**
>
> Add `--loki <url_or_file>` to include application log analysis:
> - Error log grouping by type
> - Warning detection
> - Exception stack traces

"""
    
    # Tempo Traces Summary (Collapsible with Full Details)
    report += "### 🔍 Slow Traces (Tempo)\n\n"
    
    if result.tempo_traces:
        import json
        
        for idx, trace in enumerate(result.tempo_traces[:10]):
            trace_id = trace.get('traceID', 'N/A')
            trace_id_short = trace_id[:16] + '...' if len(trace_id) > 16 else trace_id
            duration = trace.get('duration', 0)
            
            # Extract root span info
            spans = trace.get('spans', [])
            root_op = 'Unknown'
            status = 'OK'
            status_color = '#22C55E'
            if spans:
                root_span = spans[0]
                root_op = root_span.get('operationName', 'Unknown')
                tags = root_span.get('tags', [])
                for tag in tags:
                    if tag.get('key') == 'error' and tag.get('value'):
                        status = '🔴 Error'
                        status_color = '#EF4444'
                    elif tag.get('key') == 'http.status_code':
                        code = int(tag.get('value', 200))
                        if code >= 500:
                            status = f'🔴 {code}'
                            status_color = '#EF4444'
                        elif code >= 400:
                            status = f'🟡 {code}'
                            status_color = '#F59E0B'
            
            # Create collapsible section for each trace
            trace_json = json.dumps(trace, indent=2).replace('`', '\\`')
            report += f"""<details style="margin-bottom: 15px; border: 1px solid {status_color}; border-radius: 6px; padding: 10px;">
<summary style="cursor: pointer; font-weight: bold;">
Trace {idx+1}: <code>{trace_id_short}</code> - {duration:.0f}ms - {root_op} - {status}
</summary>

<div style="margin-top: 10px;">
<p><strong>Full Trace ID:</strong> <code>{trace_id}</code></p>
<p><strong>Duration:</strong> {duration:.2f}ms</p>
<p><strong>Operation:</strong> {root_op}</p>
<p><strong>Spans:</strong> {len(spans)}</p>

<div style="margin: 10px 0;">
<button onclick="navigator.clipboard.writeText(this.parentElement.querySelector('pre').textContent)" style="padding: 6px 12px; background: #00d9ff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">📋 Copy JSON</button>
<button onclick="
const blob = new Blob([this.parentElement.querySelector('pre').textContent], {{type: 'application/json'}});
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'trace_{trace_id[:8]}.json';
a.click();
" style="padding: 6px 12px; background: #00ffa3; color: #0a192f; border: none; border-radius: 4px; cursor: pointer;">💾 Download JSON</button>
<pre style="margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px; overflow-x: auto; font-size: 11px; color: #1a1a1a;">{trace_json}</pre>
</div>
</div>

</details>

"""
        
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
        report += "### 📝 Detailed Analysis\n\n"
        report += enhanced_analysis
        report += "\n"
    elif result.llm_error:
        # LLM was attempted but failed - show error with troubleshooting
        report += f"""> ⚠️ **AI analysis failed**
>
> **Error:** `{result.llm_error}`
>
> **Troubleshooting:**

"""
        # Provide context-specific help based on error type
        error_lower = result.llm_error.lower()
        if "connection" in error_lower or "refused" in error_lower:
            report += """> - Ollama is not running
> - **Fix:** Run `systemctl start ollama` or `ollama serve`
> - **Alternative:** Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable

"""
        elif "unauthorized" in error_lower or "api key" in error_lower:
            report += """> - Invalid or missing API key
> - **Fix:** Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable
> - **Alternative:** Use local Ollama with `heimr setup-llm`

"""
        elif "model" in error_lower or "not found" in error_lower:
            report += f"""> - Model not available on LLM server
> - **Fix:** Run `ollama pull qwen3.5:9b` or specify a different model with `--llm-model`
> - **Check available models:** `ollama list`

"""
        else:
            report += """> - Run `heimr setup-llm` for automated Ollama setup
> - Or use `--llm-url` and `--llm-model` to specify custom LLM
> - Add `--no-llm` to skip AI analysis

"""
    else:
        # LLM was disabled (--no-llm flag)
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
                       print_banner, print_result_summary, generate_markdown_report_content)

if __name__ == "__main__":
    main()

# Re-export extracted helpers for external callers/tests.
load_config = _load_config_mod
normalize_config = _normalize_config_mod
merge_config_with_args = _merge_config_mod
enhance_llm_output = _enhance_llm_output_mod
create_correlation_chart = _create_correlation_chart_mod
detect_timeline_mismatch = _detect_timeline_mismatch_mod
extract_llm_tldr = _extract_llm_tldr_mod
