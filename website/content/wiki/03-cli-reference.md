# CLI Reference

[← Back to Index](../WIKI.md)

Heimr provides a robust Command Line Interface (CLI) for analyzing load tests, managing configuration, and setting up the AI environment.

## Global Flags

The following flags work with all commands:

- `--help`, `-h`: Show help message and exit.

---

## 1. `analyze`

The core command to process load test results, detect anomalies, and generate AI-powered reports.

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
    - Default: `medium` (`llama3.1:8b`).
    - Options: `small`, `medium`, `large`, or any valid model string (e.g., `gpt-4o`).

#### CI/CD & Gating
- `--fail-condition`: Fail the build if a metric exceeds a threshold.
    - Syntax: `metric > value`.
    - Examples: `--fail-condition "p99_latency > 500"`, `--fail-condition "error_rate > 1.0"`.
    - Supported metrics: `p95_latency`, `p99_latency`, `error_rate`, `throughput`.
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

## 2. `config-init`

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

## 3. `setup-llm`

Helper command to install and configure local LLMs (Ollama + Llama 3) for the AI analysis engine.

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
