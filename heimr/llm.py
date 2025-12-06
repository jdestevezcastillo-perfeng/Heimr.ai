# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import os
from typing import Dict, Any

# Model tier aliases for convenience
MODEL_TIERS = {
    'small': 'llama3.2:3b',           # ~2GB, laptops/CI/CD
    'medium': 'llama3.1:8b',          # ~5GB, default
    'large': 'qwen2.5:14b'  # ~9GB VRAM, High reasoning
}


class LLMClient:
    """
    Client for interacting with LLMs (OpenAI, Anthropic, Ollama/Local) to generate explanations.
    """

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url
        # Resolve model tier alias to actual model name
        self.model = self._resolve_model(model)
        self.provider = self._detect_provider()

    def _resolve_model(self, model: str) -> str:
        """Resolve model tier alias (small/medium/large) to actual model name."""
        if not model:
            return None
        # Check if it's a tier alias
        return MODEL_TIERS.get(model.lower(), model)

    def _detect_provider(self) -> str:
        """Auto-detect which LLM provider to use based on configuration."""
        if self.base_url:
            # Custom URL means local LLM (Ollama, vLLM, etc.)
            return "local"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            return "openai"
        else:
            raise ValueError(
                "\n" + "=" * 60 + "\n"
                "❌ No LLM configuration found!\n\n"
                "Heimr requires AI analysis. Please choose one option:\n\n"
                "Option 1 - Local LLM (Recommended, Privacy-First):\n"
                "  Run: heimr setup-llm\n"
                "  This installs Ollama + Llama 3.1 (~6GB)\n\n"
                "Option 2 - OpenAI API (Cloud):\n"
                "  Set: export OPENAI_API_KEY='sk-...'\n\n"
                "Option 3 - Anthropic API (Cloud):\n"
                "  Set: export ANTHROPIC_API_KEY='sk-ant-...'\n\n"
                "Option 4 - Statistical Analysis Only:\n"
                "  Add: --no-llm (anomaly detection only, no AI insights)\n"
                + "=" * 60
            )

    def generate_explanation(self,
                             summary_stats: Dict[str,
                                                 Any],
                             anomalies_summary: Dict[str,
                                                     Any],
                             prom_metrics: Dict[str,
                                                Any] = None,
                             loki_logs: list = None,
                             tempo_traces: list = None):
        """
        Generates a natural language explanation based on test stats, anomalies, and observability data.
        Returns a generator that yields chunks of the explanation.
        """
        if self.provider == "openai":
            yield from self._generate_openai_explanation(
                summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        elif self.provider == "anthropic":
            yield from self._generate_anthropic_explanation(
                summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        elif self.provider == "local":
            yield from self._generate_local_explanation(
                summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented.")

    def _generate_openai_explanation(self,
                                     stats: Dict[str,
                                                 Any],
                                     anomalies: Dict[str,
                                                     Any],
                                     prom_metrics: Dict[str,
                                                        Any] = None,
                                     loki_logs: list = None,
                                     tempo_traces: list = None):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            prompt = self._construct_prompt(stats, anomalies, prom_metrics, loki_logs, tempo_traces)
            model_to_use = self.model if self.model else "gpt-5.1"

            stream = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a performance engineering expert. "
                                   "Analyze the following load test results."
                    },
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except ImportError:
            yield "Error: `openai` package not installed. Run `pip install openai`."
        except Exception as e:
            yield f"Error calling OpenAI: {e}"

    def _generate_anthropic_explanation(self,
                                        stats: Dict[str,
                                                    Any],
                                        anomalies: Dict[str,
                                                        Any],
                                        prom_metrics: Dict[str,
                                                           Any] = None,
                                        loki_logs: list = None,
                                        tempo_traces: list = None):
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            prompt = self._construct_prompt(stats, anomalies, prom_metrics, loki_logs, tempo_traces)

            with client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except ImportError:
            yield "Error: `anthropic` package not installed. Run `pip install anthropic`."
        except Exception as e:
            yield f"Error calling Anthropic: {e}"

    def _generate_local_explanation(self,
                                    stats: Dict[str,
                                                Any],
                                    anomalies: Dict[str,
                                                    Any],
                                    prom_metrics: Dict[str,
                                                       Any] = None,
                                    loki_logs: list = None,
                                    tempo_traces: list = None):
        """
        Generates explanation using Ollama or other local LLMs that support OpenAI-compatible API.
        """
        try:
            from openai import OpenAI

            # Use provided URL or default to Ollama
            base_url = self.base_url if self.base_url else "http://localhost:11434/v1"
            api_key = "not-needed"  # Most local LLMs don't require API keys

            client = OpenAI(api_key=api_key, base_url=base_url)
            prompt = self._construct_prompt(stats, anomalies, prom_metrics, loki_logs, tempo_traces)
            model_to_use = self.model if self.model else "llama3"

            stream = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a performance engineering expert. "
                                   "Analyze the following load test results."
                    },
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except ImportError:
            yield "Error: `openai` package not installed. Run `pip install openai`."
        except Exception as e:
            yield f"Error calling Local LLM: {e}"

    def _construct_prompt(self,
                          stats: Dict[str,
                                      Any],
                          anomalies: Dict[str,
                                          Any],
                          prom_metrics: Dict[str,
                                             Any] = None,
                          loki_logs: list = None,
                          tempo_traces: list = None) -> str:
        # Format Prometheus Metrics with actual values and statistics
        prom_text = self._format_prometheus_metrics(prom_metrics)

        # Format Loki Logs with categorization and summary
        logs_text = self._format_loki_logs(loki_logs)

        # Format Tempo Traces with detailed span analysis
        traces_text = self._format_tempo_traces(tempo_traces)

        return f"""
You are a Senior Performance Engineer. Analyze the following load test results and generate a comprehensive Root Cause Analysis (RCA) report in Markdown format.

### Test Statistics
- Total Requests: {stats.get('total_requests')}
- Average Latency: {stats.get('avg_latency'):.2f} ms
- Median Latency: {stats.get('median_latency', 0):.2f} ms
- P99 Latency: {stats.get('p99_latency'):.2f} ms
- Min Latency: {stats.get('min_latency', 0):.2f} ms
- Max Latency: {stats.get('max_latency', 0):.2f} ms
- Error Rate: {stats.get('error_rate'):.2f}%
- Error Count: {stats.get('error_count', 0)}
- Throughput: {stats.get('throughput', 0):.2f} req/s
- Start Time: {stats.get('start_time')}
- End Time: {stats.get('end_time')}

### Anomaly Detection Results
- Anomalies Detected: {anomalies.get('count')}
- Average Latency during Anomalies: {anomalies.get('avg_latency', 0):.2f} ms
- Max Latency during Anomalies: {anomalies.get('max_latency', 0):.2f} ms
- Anomaly Timestamps: {', '.join(str(ts) for ts in anomalies.get('timestamps', [])[:5])} ...

### System Metrics (Prometheus)
{prom_text}

### Application Logs (Loki)
{logs_text}

### Distributed Traces (Tempo)
{traces_text}

### Report Requirements
Please structure your response exactly as follows:

# Performance Analysis Report

## 1. Executive Summary
[Provide a concise, high-level summary for business stakeholders. Focus on whether the system met its goals, the impact of any failures, and the overall user experience. Avoid technical jargon here.]

## 2. Key Performance Indicators
[KPI_TABLE]

## 3. Technical Analysis
[Provide a detailed technical breakdown for engineers. Discuss:]
- **Latency Distribution**: Analyze Avg vs P99 vs Max. Comment on the spread and what it indicates.
- **Resource Utilization**: Analyze CPU and memory patterns. Identify bottlenecks.
- **Throughput & Errors**: Discuss load handling, error patterns, and HTTP status codes.
- **Anomalies**: Correlate detected anomalies with system events, resource spikes, or specific operations.
- **Root Cause Analysis**: Based on ALL the data above, hypothesize the most likely causes.
- **Recommendations**: Prioritized technical steps to resolve issues.
"""

    def _format_prometheus_metrics(self, prom_metrics: Dict[str, Any]) -> str:
        """Extract actual statistics from Prometheus metrics."""
        if not prom_metrics:
            return "No Prometheus metrics available."

        sections = []

        for metric_name, metric_data in prom_metrics.items():
            if not metric_data or len(metric_data) == 0:
                sections.append(f"**{metric_name}**: No data available")
                continue

            # Handle both list of series and single series
            all_values = []
            pod_summaries = []

            for series in metric_data:
                pod_name = series.get('metric', {}).get('pod', 'unknown')
                values = series.get('values', [])

                if not values:
                    continue

                # Extract numeric values (format: [timestamp, "value_string"])
                numeric_values = []
                for v in values:
                    try:
                        numeric_values.append(float(v[1]))
                    except (ValueError, IndexError):
                        continue

                if not numeric_values:
                    continue

                all_values.extend(numeric_values)

                # Calculate stats for this series
                avg_val = sum(numeric_values) / len(numeric_values)
                min_val = min(numeric_values)
                max_val = max(numeric_values)

                # Calculate trend (first vs last quarter)
                if len(numeric_values) >= 4:
                    quarter = len(numeric_values) // 4
                    first_quarter_avg = sum(numeric_values[:quarter]) / quarter
                    last_quarter_avg = sum(numeric_values[-quarter:]) / quarter
                    trend = ((last_quarter_avg - first_quarter_avg) /
                             first_quarter_avg * 100) if first_quarter_avg != 0 else 0
                    trend_text = f"{'↑' if trend > 0 else '↓'}{abs(trend):.1f}%"
                else:
                    trend_text = "N/A"

                # Format based on metric type
                if 'cpu' in metric_name.lower():
                    pod_summaries.append(
                        f"  - Pod '{pod_name}': Avg={avg_val * 100:.1f}%, Min={min_val * 100:.1f}%, "
                        f"Max={max_val * 100:.1f}%, Trend={trend_text}"
                    )
                elif 'memory' in metric_name.lower():
                    # Convert bytes to MB
                    pod_summaries.append(
                        f"  - Pod '{pod_name}': Avg={avg_val / 1024 / 1024:.1f}MB, "
                        f"Min={min_val / 1024 / 1024:.1f}MB, Max={max_val / 1024 / 1024:.1f}MB, Trend={trend_text}"
                    )
                else:
                    pod_summaries.append(
                        f"  - Pod '{pod_name}': Avg={avg_val:.2f}, Min={min_val:.2f}, "
                        f"Max={max_val:.2f}, Trend={trend_text}"
                    )

            if all_values:
                overall_max = max(all_values)

                # Add warning thresholds
                warning = ""
                if 'cpu' in metric_name.lower() and overall_max > 0.8:
                    warning = " ⚠️ HIGH CPU DETECTED"
                elif 'memory' in metric_name.lower():
                    # Check for memory growth
                    if len(all_values) >= 2:
                        growth = (all_values[-1] - all_values[0]) / all_values[0] if all_values[0] != 0 else 0
                        if growth > 0.5:
                            warning = f" ⚠️ MEMORY GROWTH: {growth * 100:.1f}%"

                sections.append(f"**{metric_name}**:{warning}\n" + "\n".join(pod_summaries))
            else:
                sections.append(f"**{metric_name}**: No valid data points")

        return "\n\n".join(sections) if sections else "No Prometheus metrics available."

    def _format_loki_logs(self, loki_logs: list) -> str:
        """Categorize and summarize logs."""
        if not loki_logs:
            return "No logs available."

        # Categorize logs by level
        log_counts = {'error': 0, 'warn': 0, 'info': 0, 'debug': 0, 'unknown': 0}
        error_messages = []
        warn_messages = []
        status_codes = {}

        for log in loki_logs:
            log_lower = log.lower() if isinstance(log, str) else str(log).lower()

            # Count by level
            if 'level=error' in log_lower or 'error' in log_lower:
                log_counts['error'] += 1
                error_messages.append(log[:200] if len(log) > 200 else log)
            elif 'level=warn' in log_lower or 'warning' in log_lower:
                log_counts['warn'] += 1
                warn_messages.append(log[:200] if len(log) > 200 else log)
            elif 'level=info' in log_lower:
                log_counts['info'] += 1
            elif 'level=debug' in log_lower:
                log_counts['debug'] += 1
            else:
                log_counts['unknown'] += 1

            # Extract HTTP status codes
            import re
            status_match = re.search(r'status[=:\s]*(\d{3})', log_lower)
            if status_match:
                code = status_match.group(1)
                status_codes[code] = status_codes.get(code, 0) + 1

        # Build summary
        sections = [f"**Log Summary** (Total: {len(loki_logs)} logs)"]
        sections.append(f"- Errors: {log_counts['error']}, Warnings: {log_counts['warn']}, Info: {log_counts['info']}")

        if status_codes:
            status_summary = ", ".join([f"{code}: {count}" for code, count in sorted(status_codes.items())])
            sections.append(f"- HTTP Status Codes: {status_summary}")

        if error_messages:
            sections.append(f"\n**Error Samples** ({min(5, len(error_messages))} of {len(error_messages)}):")
            for msg in error_messages[:5]:
                sections.append(f"  - {msg}")

        if warn_messages:
            sections.append(f"\n**Warning Samples** ({min(3, len(warn_messages))} of {len(warn_messages)}):")
            for msg in warn_messages[:3]:
                sections.append(f"  - {msg}")

        return "\n".join(sections)

    def _format_tempo_traces(self, tempo_traces: list) -> str:
        """Extract detailed trace information including spans and operations."""
        if not tempo_traces:
            return "No slow traces available."

        # Analyze traces
        operations = {}
        status_codes = {}
        durations = []
        span_details = []

        for trace in tempo_traces:
            trace_id = trace.get('traceID', 'N/A')
            spans = trace.get('spans', [])

            # Handle Tempo API format (might have 'duration' at trace level)
            trace_duration = trace.get('duration', 0)
            if trace_duration:
                durations.append(trace_duration / 1000)  # Convert µs to ms

            for span in spans:
                op_name = span.get('operationName', 'unknown')
                span_duration = span.get('duration', 0) / 1000  # Convert µs to ms

                if span_duration:
                    durations.append(span_duration)

                # Count operations
                operations[op_name] = operations.get(op_name, 0) + 1

                # Extract status codes from tags
                tags = span.get('tags', [])
                for tag in tags:
                    if tag.get('key') == 'http.status_code':
                        code = str(tag.get('value', 'unknown'))
                        status_codes[code] = status_codes.get(code, 0) + 1

                # Store span detail for top slowest
                span_details.append({
                    'trace_id': trace_id[:16] + '...' if len(trace_id) > 16 else trace_id,
                    'operation': op_name,
                    'duration': span_duration,
                    'status': next((tag.get('value') for tag in tags if tag.get('key') == 'http.status_code'), 'N/A')
                })

        # Build summary
        sections = [f"**Trace Summary** (Total: {len(tempo_traces)} slow traces analyzed)"]

        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            sections.append(
                f"- Duration Stats: Avg={avg_duration:.2f}ms, Min={min_duration:.2f}ms, Max={max_duration:.2f}ms"
            )

        if operations:
            op_summary = ", ".join([f"'{op}': {count}" for op, count in sorted(
                operations.items(), key=lambda x: -x[1])[:5]])
            sections.append(f"- Operations: {op_summary}")

        if status_codes:
            status_summary = ", ".join([f"{code}: {count}" for code, count in sorted(status_codes.items())])
            sections.append(f"- HTTP Status Codes: {status_summary}")

        # Top slowest spans
        if span_details:
            span_details.sort(key=lambda x: -x['duration'])
            sections.append("\n**Slowest Spans** (Top 5):")
            for span in span_details[:5]:
                sections.append(
                    f"  - {span['operation']}: {span['duration']:.2f}ms (Status: {span['status']}, Trace: {span['trace_id']})"
                )

        return "\n".join(sections)
