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
