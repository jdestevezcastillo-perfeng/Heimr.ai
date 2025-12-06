# Heimr.ai Wiki

Welcome to the comprehensive documentation for Heimr.ai.

## 📚 Table of Contents

1. [Architecture](#architecture)
2. [CLI Reference](#cli-reference)
3. [Configuration](#configuration)
4. [Failure Scenarios](#failure-scenarios)
5. [Troubleshooting](#troubleshooting)

---

## Architecture

Heimr operates as a pipeline:

```text
Load Test Results → Parser → Anomaly Detector → Multi-Signal Analyzer → LLM → Report
                       ↓            ↓                    ↓
                  Prometheus    Loki Logs          Tempo Traces
```

### Core Components

- **Parsers**: Normalize data from JMeter, k6, Gatling, and Locust into a standard DataFrame format.
- **Anomaly Detector**: Uses statistical methods (Mean + 2.5 STD, Bimodal detection using P99/P50 ratio) to flag performance issues.
- **LLM Client**: Connects to local (Ollama) or cloud (OpenAI/Anthropic) models to generate explainable root cause analysis.
- **Observability Clients**: Fetch correlated metrics, logs, and traces for the exact test duration.

---

## CLI Reference

### `analyze`

Analyze load test results.

```bash
heimr analyze [FILE] [OPTIONS]
```

**Arguments:**

- `FILE`: Path to load test result file (.jtl, .json, .log, .csv)

**Options:**

- `--config`: Path to config file (default: `heimr.yaml`)
- `--output`: Output file path (default: `report.md`)
- `--prometheus`: Prometheus URL or path to metrics file (auto-detected)
- `--loki`: Loki URL or path to logs file (auto-detected)
- `--tempo`: Tempo URL or path to traces file (auto-detected)
- `--llm-url`: LLM API URL (default: `http://localhost:11434/v1`)
- `--llm-model`: Model name (default: `llama3.1:8b`)
- `--explain/--no-explain`: Enable/disable LLM explanations (default: True)

### `config-init`

Generates a template configuration file (`heimr.yaml`) in the current directory. This is the easiest way to get started without typing long command-line arguments.

```bash
# Create heimr.yaml in current dir
heimr config-init

# Create with custom name
heimr config-init my_config.yaml
```

---

## Configuration

Heimr looks for a configuration file only when specified via `--config`. CLI arguments always take precedence over configuration file values.

### Example `heimr.yaml`

```yaml
# ============================================================================
# Observability Sources
# ============================================================================
# Heimr can fetch data from live URLs OR read from local JSON files.
# It automatically detects if the value is a URL (starts with http) or a file path.

# Prometheus (Metrics)
prometheus: http://localhost:9090   # Default Prometheus URL
# prometheus: ./data/metrics.json     # Or local file

# Loki (Logs)
loki: http://localhost:3100          # Default Loki URL
# loki: ./data/logs.json               # Or local file

# Tempo (Traces)
tempo: http://localhost:3200          # Default Tempo URL
# tempo: ./data/traces.json            # Or local file

# ============================================================================
# AI Analysis
# ============================================================================
# Heimr supports both local (Ollama) and cloud (OpenAI, Anthropic) models.

# 1. Local LLM (Ollama) - Recommended for Privacy
# ----------------------------------------------------------------------------
llm_url: http://localhost:11434/v1  # Default Ollama API URL
llm_model: llama3.1:8b              # Default model (Medium)

# Model Options (Pull these via 'ollama pull <model>'):
# - Small:  llama3.2:3b   (~2GB VRAM)  - Good for laptops, CI/CD
# - Medium: llama3.1:8b   (~5GB VRAM)  - Best balance of speed/quality [DEFAULT]
# - Large:  llama3.3:70b  (~40GB VRAM) - Maximum reasoning capability (requires powerful GPU)

# 2. Cloud LLMs (OpenAI / Anthropic)
# ----------------------------------------------------------------------------
# To use cloud models, DO NOT set llm_url (leave it commented or empty).
# Instead, set the following environment variables:
#   export OPENAI_API_KEY="sk-..."      -> uses gpt-4o by default
#   export ANTHROPIC_API_KEY="sk-..."   -> uses claude-3-5-sonnet by default
#
# You can override the specific cloud model name using llm_model:
# llm_model: gpt-4-turbo

# ============================================================================
# Reporting
# ============================================================================
output: ./reports/analysis.md
format: jtl  # optional override (jtl, k6, gatling, locust)
```

---

## Failure Scenarios

Heimr is trained to recognize patterns across these categories:

### Performance

- **Latency Spikes**: Sudden increases in P99/Max latency.
- **Bimodal Distribution**: Indicates mixed performance characteristics (e.g., cache hits vs misses).
- **Gradual Degradation**: Linearly increasing response times (memory leaks).

### Infrastructure

- **CPU Saturation**: Sustained high CPU usage correlating with latency.
- **Memory Leaks**: JVM/Container memory growing without reclamation.
- **OOMKills**: Sudden pod restarts or process termination.

### Application

- **Database Bottlenecks**: Slow queries, connection pool exhaustion.
- **Cache Issues**: Stampedes, low hit rates.
- **Dependency Failures**: Slow downstream services (via tracing).

---

## Troubleshooting

### "No anomalies detected"

- Ensure your test duration is long enough (>1 minute).
- Check if your observability data overlaps with the test timeframe. Timesync is critical.

### "LLM connection failed"

- Verify Ollama is running: `curl http://localhost:11434`.
- Check if the model is pulled: `ollama list`.

### "Parser error"

- Ensure you have the correct file format.
- **JMeter**: CSV format required.
- **k6**: JSON output (`--out json=results.json`).
- **Locust**: CSV stats history.
