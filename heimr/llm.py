# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
import os
from typing import Dict, Any

class LLMClient:
    """
    Client for interacting with LLMs (OpenAI, Anthropic, Ollama/Local) to generate explanations.
    """
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url
        self.model = model
        self.provider = self._detect_provider()

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
                "No LLM provider configured. Please either:\n"
                "  - Set OPENAI_API_KEY environment variable, or\n"
                "  - Set ANTHROPIC_API_KEY environment variable, or\n"
                "  - Provide --llm-url for local LLM (e.g., http://localhost:11434/v1)"
            )

    def generate_explanation(self, summary_stats: Dict[str, Any], anomalies_summary: Dict[str, Any], prom_metrics: Dict[str, Any] = None, loki_logs: list = None, tempo_traces: list = None):
        """
        Generates a natural language explanation based on test stats, anomalies, and observability data.
        Returns a generator that yields chunks of the explanation.
        """
        if self.provider == "openai":
            yield from self._generate_openai_explanation(summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        elif self.provider == "anthropic":
            yield from self._generate_anthropic_explanation(summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        elif self.provider == "local":
            yield from self._generate_local_explanation(summary_stats, anomalies_summary, prom_metrics, loki_logs, tempo_traces)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented.")

    def _generate_openai_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any], prom_metrics: Dict[str, Any] = None, loki_logs: list = None, tempo_traces: list = None):
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            prompt = self._construct_prompt(stats, anomalies, prom_metrics, loki_logs, tempo_traces)
            model_to_use = self.model if self.model else "gpt-5.1"
            
            stream = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are a performance engineering expert. Analyze the following load test results."},
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

    def _generate_anthropic_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any], prom_metrics: Dict[str, Any] = None, loki_logs: list = None, tempo_traces: list = None):
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            prompt = self._construct_prompt(stats, anomalies, prom_metrics, loki_logs, tempo_traces)
            
            with client.messages.stream(
                model="claude-sonnet-4-5-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except ImportError:
            yield "Error: `anthropic` package not installed. Run `pip install anthropic`."
        except Exception as e:
            yield f"Error calling Anthropic: {e}"

    def _generate_local_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any], prom_metrics: Dict[str, Any] = None, loki_logs: list = None, tempo_traces: list = None):
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
                    {"role": "system", "content": "You are a performance engineering expert. Analyze the following load test results."},
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

    def _construct_prompt(self, stats: Dict[str, Any], anomalies: Dict[str, Any], prom_metrics: Dict[str, Any] = None, loki_logs: list = None, tempo_traces: list = None) -> str:
        # Format Prometheus Metrics
        prom_text = "No Prometheus metrics available."
        if prom_metrics:
            prom_text = "Prometheus Metrics:\\n"
            for metric, values in prom_metrics.items():
                prom_text += f"- {metric}: {len(values)} data points\\n"

        # Format Loki Logs
        logs_text = "No logs available."
        if loki_logs:
            logs_text = "Error Logs (Sample):\\n"
            for log in loki_logs[:10]:
                logs_text += f"- {log}\\n"

        # Format Tempo Traces
        traces_text = "No slow traces available."
        if tempo_traces:
            traces_text = "Slow Traces (Sample):\\n"
            for trace in tempo_traces[:5]:
                trace_id = trace.get('traceID', 'N/A')
                duration = trace.get('duration', 'N/A')
                traces_text += f"- TraceID: {trace_id}, Duration: {duration}ms\\n"

        return f"""
You are a Senior Performance Engineer. Analyze the following load test results and generate a comprehensive Root Cause Analysis (RCA) report in Markdown format.

### Test Statistics
- Total Requests: {stats.get('total_requests')}
- Average Latency: {stats.get('avg_latency'):.2f} ms
- P99 Latency: {stats.get('p99_latency'):.2f} ms
- Error Rate: {stats.get('error_rate'):.2f}%
- Start Time: {stats.get('start_time')}
- End Time: {stats.get('end_time')}

### Anomaly Detection Results
- Anomalies Detected: {anomalies.get('count')}
- Average Latency during Anomalies: {anomalies.get('avg_latency', 0):.2f} ms
- Max Latency during Anomalies: {anomalies.get('max_latency', 0):.2f} ms
- Anomaly Timestamps: {', '.join(str(ts) for ts in anomalies.get('timestamps', [])[:5])} ...

### Observability Data
{prom_text}

{logs_text}

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
- **Latency Distribution**: Analyze Avg vs P99 vs Max.
- **Throughput & Errors**: Discuss load handling and error patterns.
- **Anomalies**: Correlate detected anomalies with system events.
- **Root Cause Analysis**: Hypothesize causes (e.g., DB saturation, network).
- **Recommendations**: Technical steps to resolve issues.
"""
