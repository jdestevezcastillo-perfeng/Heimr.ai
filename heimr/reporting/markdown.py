# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
from __future__ import annotations

from typing import Any, Dict

from heimr.analyzer import AnalysisResult


def enhance_llm_output(llm_text: str, result: AnalysisResult) -> str:
    import re

    if not llm_text:
        return llm_text

    enhanced = llm_text
    annotations = []

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

    if correlations_found and result.df is not None and not result.df.empty:
        for corr in correlations_found[:2]:
            if isinstance(corr, tuple) and len(corr) == 2:
                metric1 = corr[0].strip().lower()
                metric2 = corr[1].strip().lower()

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

                if 'timestamp_dt' in result.df.columns:
                    try:
                        chart_html = create_correlation_chart(result.df, col1, col2, metric1, metric2)
                        if chart_html:
                            annotations.append(f"\n\n{chart_html}\n\n")
                    except Exception:
                        pass

    if correlations_found:
        badge = "\n\n> 📊 **Correlations Detected**: "
        for corr in correlations_found[:3]:
            if isinstance(corr, tuple):
                badge += f"`{corr[0].strip()}` ↔ `{corr[1].strip()}`, "
            else:
                badge += f"`{corr.strip()}`, "
        badge = badge.rstrip(", ") + "\n"
        annotations.append(badge)

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

    if result.loki_logs and ('error log' in enhanced.lower() or 'logs show' in enhanced.lower()):
        log_samples = result.loki_logs[:3]
        if log_samples:
            log_box = "\n\n<details>\n<summary>📜 Referenced Error Logs (click to expand)</summary>\n\n```\n"
            for log in log_samples:
                log_str = str(log)[:200]
                log_box += f"{log_str}\n"
            log_box += "```\n</details>\n"
            annotations.append(log_box)

    if annotations:
        enhanced += "\n\n---\n### 🔗 Analysis Insights\n"
        enhanced += "\n".join(annotations)

    return enhanced


def create_correlation_chart(df, col1, col2, label1, label2):
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        df_sorted = df.sort_values('timestamp_dt')
        df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('30s')

        agg_dict = {}
        if col1 in df_sorted.columns or col1 == 'elapsed':
            agg_dict[col1 if col1 in df_sorted.columns else 'elapsed'] = 'mean'
        if col2 in df_sorted.columns or col2 == 'elapsed':
            agg_dict[col2 if col2 in df_sorted.columns else 'elapsed'] = 'mean'

        if not agg_dict:
            return None

        agg = df_sorted.groupby('time_bucket').agg(agg_dict).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

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


def detect_timeline_mismatch(result: AnalysisResult) -> dict:
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

    test_start = df['timestamp_dt'].min()
    test_end = df['timestamp_dt'].max()
    mismatch['test_start'] = test_start
    mismatch['test_end'] = test_end

    if result.prom_metrics:
        try:
            from heimr.prometheus_normalizer import PrometheusNormalizer
            import pandas as pd

            normalizer = PrometheusNormalizer()
            prom_df = normalizer.normalize(result.prom_metrics)
            if prom_df is not None and not prom_df.empty and 'timestamp_dt' in prom_df.columns:
                prom_start = prom_df['timestamp_dt'].min()
                prom_end = prom_df['timestamp_dt'].max()
                mismatch['prom_start'] = prom_start
                mismatch['prom_end'] = prom_end

                overlap_start = max(test_start, prom_start)
                overlap_end = min(test_end, prom_end)
                overlap_seconds = max((overlap_end - overlap_start).total_seconds(), 0)
                test_seconds = (test_end - test_start).total_seconds()
                overlap_pct = (overlap_seconds / test_seconds * 100) if test_seconds > 0 else 0
                mismatch['overlap_pct'] = overlap_pct

                if overlap_pct < 70:
                    mismatch['has_mismatch'] = True
                    mismatch['message'] = (
                        f"⚠️ Observability data only overlaps {overlap_pct:.0f}% of the test window "
                        f"({prom_start.strftime('%H:%M:%S')}→{prom_end.strftime('%H:%M:%S')} vs "
                        f"{test_start.strftime('%H:%M:%S')}→{test_end.strftime('%H:%M:%S')}). "
                        "Correlations may be incomplete."
                    )
        except Exception:
            pass

    return mismatch


def extract_llm_tldr(llm_text: str, llm_client=None) -> dict:
    import re

    tldr = {'root_cause': '', 'fix': ''}

    prompt = f"""Summarize the following performance RCA into two short lines.
Format strictly:
ROOT_CAUSE: <one sentence>
FIX: <one sentence>

RCA:
{llm_text[:2000]}
"""

    if llm_client:
        try:
            if llm_client.provider == 'openai':
                model = llm_client.model or "gpt-4"
                import openai
                client = openai.OpenAI(base_url=llm_client.base_url, api_key=llm_client.api_key or "dummy")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=250,
                    timeout=getattr(llm_client, "timeout_sec", None),
                )
                result_text = response.choices[0].message.content
            elif llm_client.provider == 'anthropic':
                model = llm_client.model or "claude-3-sonnet-20240229"
                import anthropic
                client = anthropic.Anthropic(api_key=llm_client.api_key)
                response = client.messages.create(
                    model=model,
                    max_tokens=250,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=getattr(llm_client, "timeout_sec", None),
                )
                result_text = response.content[0].text
            else:
                model = llm_client.model or "qwen3.5:9b"
                import openai
                client = openai.OpenAI(base_url=llm_client.base_url, api_key="ollama")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=250,
                    timeout=getattr(llm_client, "timeout_sec", None),
                )
                result_text = response.choices[0].message.content

            root_match = re.search(r'ROOT_CAUSE:\s*(.+?)(?:\n|$)', result_text, re.IGNORECASE)
            fix_match = re.search(r'FIX:\s*(.+?)(?:\n|$)', result_text, re.IGNORECASE)

            if root_match:
                tldr['root_cause'] = root_match.group(1).strip()[:250]
            if fix_match:
                tldr['fix'] = fix_match.group(1).strip()[:250]

            if not tldr['root_cause'] or not tldr['fix']:
                print(f"⚠️  TLDR LLM returned unexpected format. Response: {result_text[:200]}")
                tldr['root_cause'] = "⚠️ TLDR generation failed - LLM response format error"
                tldr['fix'] = "⚠️ See detailed analysis below"

        except Exception as e:
            print(f"⚠️  TLDR LLM call failed: {e}")
            tldr['root_cause'] = "⚠️ TLDR generation failed - LLM error"
            tldr['fix'] = "⚠️ See detailed analysis below"
    else:
        tldr['root_cause'] = "⚠️ TLDR unavailable - no LLM configured"
        tldr['fix'] = "⚠️ See detailed analysis below"

    return tldr


def generate_markdown_report_content(result: AnalysisResult, args) -> str:
    """Generate the full markdown report content."""
    df = result.df
    kpi_data = result.kpi

    has_anomalies = result.anomaly_summary.get('count', 0) > 0
    has_errors = kpi_data['errors']['rate'] > 0
    has_loki_errors = len(result.loki_logs) > 0
    has_slow_traces = len(result.tempo_traces) > 5

    if has_anomalies or kpi_data['errors']['rate'] > 1.0:
        status = "FAILED"
        status_color = "#EF4444"
    elif has_loki_errors or has_slow_traces or has_errors:
        status = "WARNING"
        status_color = "#F59E0B"
    else:
        status = "OK"
        status_color = "#22C55E"

    report = ""

    import json
    import os
    import re
    from datetime import datetime

    test_file = os.path.basename(args.file) if hasattr(args, 'file') else 'Unknown'
    test_start = df['timestamp_dt'].min() if not df.empty and 'timestamp_dt' in df.columns else None
    test_end = df['timestamp_dt'].max() if not df.empty and 'timestamp_dt' in df.columns else None

    report += """<div style="background: #0a192f; border: 1px solid #00d9ff33; padding: 15px; margin-bottom: 20px; border-radius: 6px; font-size: 13px;">

### 📊 Report Metadata

"""

    report += f"**Load Test File:** `{test_file}`\n\n"

    if test_start and test_end:
        test_duration = (test_end - test_start).total_seconds()
        report += f"**Test Period:** {test_start.strftime('%Y-%m-%d %H:%M:%S')} → {test_end.strftime('%H:%M:%S')} ({test_duration/60:.1f} minutes)\n\n"

    grafana_url = getattr(args, "grafana_url", None)
    grafana_uid = getattr(args, "grafana_dashboard_uid", None)
    if grafana_url and grafana_uid and test_start and test_end:
        from urllib.parse import quote
        base = grafana_url.rstrip("/")
        frm = int(test_start.timestamp() * 1000)
        to = int(test_end.timestamp() * 1000)
        dash_url = f"{base}/d/{quote(grafana_uid)}?from={frm}&to={to}"
        report += f"**Grafana Dashboard:** {dash_url}\n\n"

    if result.prom_metrics:
        prom_times = []
        for _, metric_data in result.prom_metrics.items():
            if isinstance(metric_data, dict) and 'data' in metric_data and 'result' in metric_data['data']:
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

    timeline_info = detect_timeline_mismatch(result)
    if timeline_info['has_mismatch']:
        report += f"> {timeline_info['message']}\n\n"

    report += "## 📊 Key Metrics\n\n"
    report += "| Total Reqs | Throughput | Avg | P50 | P95 | P99 | Max | Error Rate | Anomalies |\n"
    report += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"

    anomaly_count = result.anomaly_summary.get('count', 0)
    total_reqs = kpi_data['throughput']['total_requests']
    rps = kpi_data['throughput']['requests_per_second']
    lat = kpi_data['latency']
    p50 = lat.get('p50', 0)
    p95 = lat.get('p95', 0)
    p99 = lat.get('p99', 0)
    avg = lat.get('avg', 0)
    max_lat = lat.get('max', 0)

    report += f"| **{total_reqs:,}** | **{rps:.1f}** req/s | **{avg:.0f}** ms | **{p50:.0f}** ms | **{p95:.0f}** ms | **{p99:.0f}** ms | **{max_lat:.0f}** ms | **{error_rate:.2f}%** | **{anomaly_count}** |\n\n"

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
            endpoint_lat = data.get("latency", {})
            report += (
                f"| `{name}` | {data.get('total_requests', 0)} | {data.get('throughput_rps', 0):.2f} | "
                f"{data.get('error_rate', 0):.2f}% | {endpoint_lat.get('p50', 0):.0f} | "
                f"{endpoint_lat.get('p95', 0):.0f} | {endpoint_lat.get('p99', 0):.0f} |\n"
            )
        report += "\n"

    if has_anomalies:
        if not df.empty and 'endpoint' in df.columns:
            endpoint_p99 = df.groupby('endpoint')['elapsed'].quantile(0.99)
            worst = endpoint_p99.idxmax()
            report += f"> 💡 **Recommendation**: Investigate `{worst}` — P99 latency is {endpoint_p99[worst]:.0f}ms\n\n"
    elif has_loki_errors:
        report += f"> 💡 **Recommendation**: Review {len(result.loki_logs)} error logs in Loki for application issues\n\n"
    elif has_slow_traces:
        report += f"> 💡 **Recommendation**: Analyze {len(result.tempo_traces)} slow traces in Tempo for bottlenecks\n\n"

    if getattr(args, "tag", None):
        report += "### Build Context\n"
        report += "| Key | Value |\n|---|---|\n"
        for tag in args.tag:
            if '=' in tag:
                k, v = tag.split('=', 1)
                report += f"| **{k}** | `{v}` |\n"
            else:
                report += f"| **Tag** | `{tag}` |\n"
        report += "\n"

    if result.llm_explanation:
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

    report += "---\n\n## 📈 Performance Charts\n\n"

    try:
        from heimr.reporting.charts import ReportCharts

        latency_chart = ReportCharts.latency_histogram(df)
        if latency_chart:
            report += "### Response Time Distribution\n\n"
            report += latency_chart + "\n\n"

        response_chart = ReportCharts.response_time_over_time(df)
        if response_chart:
            report += "### Response Time Over Load\n\n"
            report += response_chart + "\n\n"

        endpoint_chart = ReportCharts.response_time_by_endpoint(df)
        if endpoint_chart:
            report += "### Response Time by Endpoint\n\n"
            report += endpoint_chart + "\n\n"

        throughput_endpoint_chart = ReportCharts.throughput_by_endpoint(df)
        if throughput_endpoint_chart:
            report += "### Throughput by Endpoint\n\n"
            report += throughput_endpoint_chart + "\n\n"

        error_chart = ReportCharts.error_rate_with_throughput(df)
        if error_chart:
            report += "### Error Rate (with Throughput Overlay)\n\n"
            report += error_chart + "\n\n"
    except ImportError:
        report += "*Charts unavailable - install plotly: `pip install plotly kaleido`*\n\n"
    except Exception as e:
        report += f"*Chart generation error: {e}*\n\n"

    report += "---\n\n## 🖥️ Resource Utilization\n\n"

    if result.prom_metrics:
        try:
            from heimr.prometheus_normalizer import PrometheusNormalizer
            from heimr.reporting.charts import ReportCharts

            categorized = PrometheusNormalizer.categorize_metrics(result.prom_metrics)
            charts_added = False
            throughput_df = None

            if not df.empty and 'timestamp_dt' in df.columns:
                try:
                    df_sorted = df.sort_values('timestamp_dt')
                    df_sorted['time_bucket'] = df_sorted['timestamp_dt'].dt.floor('10s')
                    agg = df_sorted.groupby('time_bucket').size().reset_index(name='requests')
                    agg['rps'] = agg['requests'] / 10
                    throughput_df = agg[['time_bucket', 'rps']].rename(columns={'time_bucket': 'time'})
                except Exception:
                    pass

            metric_sections = [
                ('cpu', "### CPU Utilization"),
                ('memory', "### Memory Usage"),
                ('gpu', "### GPU Utilization"),
                ('disk', "### Disk I/O"),
                ('network', "### Network I/O"),
                ('db', "### Database Metrics"),
                ('messaging', "### Messaging/Streaming"),
                ('http', "### HTTP/Application Metrics"),
            ]

            for metric_type, title in metric_sections:
                if categorized.get(metric_type):
                    metric_chart = ReportCharts.resource_utilization(result.prom_metrics, metric_type, throughput_df)
                    if metric_chart:
                        report += f"{title}\n\n"
                        report += metric_chart + "\n\n"
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

    if result.jvm_thread_dump or result.jvm_heap_dump or result.jvm_gc_log:
        report += "---\n\n## ☕ JVM Analysis\n\n"

        try:
            from heimr.reporting.charts import ReportCharts

            if result.jvm_thread_dump:
                thread_chart = ReportCharts.thread_state_pie(result.jvm_thread_dump)
                if thread_chart:
                    report += "### Thread States\n\n"
                    report += thread_chart + "\n\n"

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

            if result.jvm_gc_log:
                gc_chart = ReportCharts.gc_pause_timeline(result.jvm_gc_log)
                if gc_chart:
                    report += "### GC Pause Timeline\n\n"
                    report += gc_chart + "\n\n"

                gc_summary = result.jvm_gc_log.get('summary', {})
                report += f"**GC Summary:** {gc_summary.get('gc_type', 'Unknown')} collector, "
                report += f"{gc_summary.get('total_events', 0)} events, "
                report += f"{gc_summary.get('total_pause_seconds', 0):.2f}s total pause time\n\n"

                if gc_summary.get('full_gc_count', 0) > 0:
                    report += f"> ⚠️ **Warning:** {gc_summary.get('full_gc_count', 0)} Full GC events detected\n\n"

            if result.jvm_heap_dump:
                heap_summary = result.jvm_heap_dump.get('heap_summary', {})
                report += "### Heap Analysis\n\n"
                report += f"**Total Heap:** {heap_summary.get('total_bytes_mb', 0):.1f} MB | "
                report += f"**Instances:** {heap_summary.get('total_instances', 0):,}\n\n"

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

                leaks = result.jvm_heap_dump.get('potential_leaks', [])
                if leaks:
                    report += "> ⚠️ **Potential Memory Leaks:**\n"
                    for leak in leaks[:3]:
                        report += f"> - `{leak.get('class_name', 'unknown')}`: {leak.get('reason', 'high instance count')}\n"
                    report += "\n"
        except Exception as e:
            report += f"*JVM chart generation error: {e}*\n\n"

    report += "---\n\n## 📋 Detailed Data Breakdown\n\n"
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
            endpoint_error_rate = (error_count / count) * 100
            avg = group['elapsed'].mean()
            p95 = group['elapsed'].quantile(0.95)
            p99 = group['elapsed'].quantile(0.99)

            error_display = f"{endpoint_error_rate:.2f}%"
            if endpoint_error_rate > 1:
                error_display = f"**{endpoint_error_rate:.2f}%** 🔴"
            elif endpoint_error_rate > 0:
                error_display = f"{endpoint_error_rate:.2f}% 🟡"

            max_latency = group['elapsed'].max()
            report += f"| `{name}` | {count:,} | {throughput:.1f} | {error_display} | {avg:.2f} | {p95:.2f} | {p99:.2f} | {max_latency:.2f} |\n"

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
    report += "### 📝 Log Analysis (Loki)\n\n"

    if result.loki_logs:
        error_groups = {}
        for log in result.loki_logs:
            log_str = str(log).lower()

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

            error_signature = None
            msg_match = re.search(r'msg="([^"]+)"', str(log))
            if msg_match:
                error_signature = msg_match.group(1)
            else:
                err_match = re.search(r'err="([^"]+)"', str(log))
                if err_match:
                    error_signature = err_match.group(1)
                else:
                    log_without_ts = re.sub(r'ts=\d{4}-\d{2}-\d{2}T[\d:\.]+Z?\s*', '', str(log))
                    error_signature = log_without_ts[:100].strip()

            if not error_signature:
                error_signature = str(log)[:100].strip()

            if error_type not in error_groups:
                error_groups[error_type] = {'count': 0, 'patterns': {}}

            error_groups[error_type]['count'] += 1

            if error_signature not in error_groups[error_type]['patterns']:
                error_groups[error_type]['patterns'][error_signature] = {'count': 0, 'sample': log}
            error_groups[error_type]['patterns'][error_signature]['count'] += 1

        for error_type, data in sorted(error_groups.items(), key=lambda x: -x[1]['count']):
            color = '#EF4444' if error_type == 'ERROR' else '#F59E0B' if error_type == 'WARNING' else '#6B7280'
            report += f"""<details style="margin-bottom: 15px; border: 1px solid {color}; border-radius: 6px; padding: 10px;">
<summary style="cursor: pointer; font-weight: bold; color: {color};">
{error_type} ({data['count']} occurrences, {len(data['patterns'])} unique patterns) - Click to expand
</summary>

"""
            for _, pattern_data in sorted(data['patterns'].items(), key=lambda x: -x[1]['count'])[:10]:
                log_text = str(pattern_data['sample']).replace('`', '\\`')
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

    report += "### 🔍 Slow Traces (Tempo)\n\n"

    if result.tempo_traces:
        for idx, trace in enumerate(result.tempo_traces[:10]):
            trace_id = trace.get('traceID', 'N/A')
            trace_id_short = trace_id[:16] + '...' if len(trace_id) > 16 else trace_id
            duration = trace.get('duration', 0)

            spans = trace.get('spans', [])
            root_op = 'Unknown'
            trace_status = 'OK'
            trace_status_color = '#22C55E'
            if spans:
                root_span = spans[0]
                root_op = root_span.get('operationName', 'Unknown')
                tags = root_span.get('tags', [])
                for tag in tags:
                    if tag.get('key') == 'error' and tag.get('value'):
                        trace_status = '🔴 Error'
                        trace_status_color = '#EF4444'
                    elif tag.get('key') == 'http.status_code':
                        code = int(tag.get('value', 200))
                        if code >= 500:
                            trace_status = f'🔴 {code}'
                            trace_status_color = '#EF4444'
                        elif code >= 400:
                            trace_status = f'🟡 {code}'
                            trace_status_color = '#F59E0B'

            trace_json = json.dumps(trace, indent=2).replace('`', '\\`')
            report += f"""<details style="margin-bottom: 15px; border: 1px solid {trace_status_color}; border-radius: 6px; padding: 10px;">
<summary style="cursor: pointer; font-weight: bold;">
Trace {idx+1}: <code>{trace_id_short}</code> - {duration:.0f}ms - {root_op} - {trace_status}
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

    report += "---\n\n## 🤖 AI Root Cause Analysis\n\n"

    if result.llm_explanation:
        enhanced_analysis = enhance_llm_output(result.llm_explanation, result)
        report += "### 📝 Detailed Analysis\n\n"
        report += enhanced_analysis
        report += "\n"
    elif result.llm_error:
        report += f"""> ⚠️ **AI analysis failed**
>
> **Error:** `{result.llm_error}`
>
> **Troubleshooting:**

"""
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
            report += """> - Model not available on LLM server
> - **Fix:** Run `ollama pull qwen3.5:9b` or specify a different model with `--llm-model`
> - **Check available models:** `ollama list`

"""
        else:
            report += """> - Run `heimr setup-llm` for automated Ollama setup
> - Or use `--llm-url` and `--llm-model` to specify custom LLM
> - Add `--no-llm` to skip AI analysis

"""
    else:
        report += """> ℹ️ **AI analysis not available.**
>
> Run without `--no-llm` to enable AI-powered root cause analysis.
> Requires Ollama with Llama 3.1 or an OpenAI API key.
>
> Quick setup: `heimr setup-llm`

"""

    return report
