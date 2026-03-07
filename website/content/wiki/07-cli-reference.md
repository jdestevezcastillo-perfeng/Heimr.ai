# CLI Reference

[← Back to Index](../WIKI.md)

Heimr provides a robust Command Line Interface (CLI) for analyzing load tests, managing configuration, and setting up the AI environment.

## Global Flags

The following flags work with all commands:

- `--help`, `-h`: Show help message and exit.

---

## 1. `agent`

The primary command. Runs Heimr as an autonomous performance engineering agent with ReAct reasoning.

```bash
heimr agent [FILE] [OPTIONS]
```

### Arguments

- **`FILE`** (Required): Path to the load test result file (same formats as `analyze`).

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config`, `-c` | — | Path to YAML configuration file |
| `--mode` | `autonomous` | Agent mode: `autonomous` or `supervised` |
| `--gate-policy` | `strict` | `strict` (fail on issues) or `advisory` (warn only) |
| `--max-iterations` | `10` | Max ReAct loop iterations |
| `--fail-condition` | — | Fail threshold (repeatable). Format: `"metric > value"` |
| `--prometheus` | — | Prometheus URL or JSON file |
| `--loki` | — | Loki URL or JSON file |
| `--tempo` | — | Tempo URL or JSON file |
| `--llm-url` | — | Override LLM API URL |
| `--llm-model` | — | Override LLM model |
| `--task` | auto | Custom task description for the agent |
| `--verbose`, `-v` | off | Print reasoning steps |
| `--log-level` | — | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `--ci-summary` | — | Generate GitHub Actions Step Summary |
| `--junit-output` | — | Path to save JUnit XML report |

### Examples

**Basic deployment gate:**
```bash
heimr agent results.json --gate-policy strict --verbose
```

**With observability and fail conditions:**
```bash
heimr agent results.json \
  --gate-policy strict \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --fail-condition "p99_latency > 500" \
  --fail-condition "error_rate > 1" \
  --verbose
```

**Advisory mode (warn but don't fail):**
```bash
heimr agent results.json --gate-policy advisory --ci-summary
```

---

## 2. `analyze`

Generates detailed performance reports with charts, per-endpoint breakdowns, and AI root cause analysis.

```bash
heimr analyze [FILE] [OPTIONS]
```

### Arguments

- **`FILE`** (Required): Path to the load test result file.
    - **Supported Formats**:
        - `.jtl`, `.csv` (JMeter)
        - `.json` (k6)
        - `.log` (Gatling)
        - `.csv` (Locust - e.g. `*_stats_history.csv`)
        - `.har` (HTTP Archive)


### Options

#### General
- `--config`, `-c`: Path to a YAML configuration file. default: `heimr.yaml`.
- `--output`: Path to save the Markdown report. default: `report.md`.
    - *Note*: A PDF report is automatically generated alongside this file (e.g., `report.pdf`).
- `--no-llm`: Disable AI analysis. Use this for faster, stats-only reports.

#### Observability Integration
Heimr correlates load test data with server-side metrics. You can provide a live URL or a local file dump.

- `--prometheus`: URL (e.g., `http://localhost:9090`) or path to JSON metrics file.
- `--loki`: URL (e.g., `http://localhost:3100`) or path to JSON logs file.
- `--tempo`: URL (e.g., `http://localhost:3200`) or path to JSON traces file.

#### AI Configuration
- `--llm-url`: Base URL for the LLM API.
    - Default: `http://localhost:11434/v1` (Ollama).
    - *Tip*: Leave empty if using Cloud API keys.
- `--llm-model`: Specific model to use.
    - Default: `medium` (`qwen3.5:9b`).
    - Options: `small`, `medium`, `large`, or any valid model string (e.g., `gpt-4o`).
- `--prompt-template`: Path to custom LLM prompt template file.
    - Use template variables like `{total_requests}`, `{p99_latency}`, `{error_rate}`, etc.
    - Available variables:
        - Test stats: `{total_requests}`, `{avg_latency}`, `{p50_latency}`, `{p95_latency}`, `{p99_latency}`, `{error_rate}`, `{throughput}`
        - Anomalies: `{anomaly_count}`, `{anomaly_timestamps}`
        - Observability: `{prometheus_metrics}`, `{loki_logs}`, `{tempo_traces}`
    - See [`examples/prompt_template_example.txt`](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/blob/main/examples/prompt_template_example.txt) for full template.

#### CI/CD & Gating
- `--fail-condition`: Fail the build if a metric exceeds a threshold.
    - Syntax: `metric > value`.
    - Examples: `--fail-condition "p99_latency > 500"`, `--fail-condition "error_rate > 1.0"`.
    - Supported metrics: `p95_latency`, `p99_latency`, `error_rate`, `throughput`.
    - Applies to single runs and baseline comparisons.
- Built-in verdict thresholds are configurable in `heimr.yaml`:
    - `cpu_threshold`, `mem_growth_threshold`, `anomaly_threshold`, `error_rate_threshold`.
- `--tag`: Add metadata to the report header. useful for tracking builds.
    - Example: `--tag "branch=main" --tag "commit=${GITHUB_SHA}"`.
- `--ci-summary`: Generate a GitHub Actions Job Summary.
- `--junit-output`: Path to save a JUnit XML report for CI test integration.

#### Baseline Comparison
- `--compare-baseline`: Path to a previous load test file to compare against.
- `--compare-prometheus`: Path to previous Prometheus metrics.
- `--compare-loki`: Path to previous Loki logs.
- `--compare-tempo`: Path to previous Tempo traces.
- `--fail-on-regression`: Fail if performance degrades by X% compared to baseline.
- `--llm-timeout-sec`: Timeout for LLM calls.
- `--llm-max-retries`: Retry count for LLM calls.
- `--log-level`: Control internal logging verbosity (default INFO).
- `--detector-mode`: Anomaly detector mode (`simple`, `mad`, `trend`).
- `--trend-threshold`: Threshold for `trend` mode (fraction, default 0.5).
- `--grafana-url`: Grafana base URL to generate dashboard links.
- `--grafana-dashboard-uid`: Grafana dashboard UID to link in reports.

### Examples

**Minimal Run (Auto-detection)**
```bash
heimr analyze tests/output/results.jtl
```

**Standard Run (with Config)**
```bash
heimr analyze tests/output/k6_results.json -c heimr.yaml
```

**CI/CD Gating with Metadata**
```bash
heimr analyze results.jtl \
  --fail-condition "p95_latency > 800" \
  --fail-condition "error_rate > 0.5" \
  --tag "build_id=123" \
  --tag "env=staging" \
  --no-llm
```

**Full AI Analysis (Cloud Model)**
```bash
export OPENAI_API_KEY="sk-..."
heimr analyze browser_session.har \
  --llm-model gpt-4o \
  --prometheus http://prometheus.internal:9090 \
  --output final_report.md
```

---

## 3. `mcp`

Starts the Heimr MCP (Model Context Protocol) server for Claude integration.

```bash
heimr mcp [OPTIONS]
```

### Options
- `--transport`: MCP transport type. (Default: `stdio`, Options: `stdio`, `streamable-http`)
- `--port`: Port for HTTP transport. (Default: `8000`)

### Examples
```bash
# stdio transport (for Claude Code / Claude Desktop)
heimr mcp

# HTTP transport (for remote/shared deployments)
heimr mcp --transport streamable-http --port 8000
```

See [MCP Integration](03-mcp-integration.md) for setup instructions.

---

## 4. `config-init`

Generates a template `heimr.yaml` configuration file to help you get started quickly.

```bash
heimr config-init [OPTIONS]
```

### Options
- `--output`, `-o`: Output path for the config file. (Default: `heimr.yaml`)

### Example
```bash
heimr config-init
# Edit the file:
# vim heimr.yaml
```

---

## 5. `setup-llm`

Helper command to install and configure local LLMs (Ollama + Qwen 3.5) for the AI analysis engine.

```bash
heimr setup-llm [OPTIONS]
```

### Options
- `--non-interactive`: Run installation automatically without user prompts (good for setup scripts).

### Example
```bash
# Interactive setup
heimr setup-llm

# CI/CD setup
heimr setup-llm --non-interactive
```
