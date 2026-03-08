# Development Guide

[← Back to Index](../WIKI.md)

Technical details for developers and contributors.

---

## Table of Contents

1. [Code Structure](#code-structure)
2. [Repository Boundaries](#repository-boundaries)
3. [Development Setup](#development-setup)
4. [Anomaly Detection](#anomaly-detection)
5. [LLM Integration](#llm-integration)
6. [Research & Decisions](#research--decisions)
7. [Testing](#testing)

---

## Code Structure

```text
heimr/
├── agent/               # ReAct loop, gate logic, MCP server
├── commands/            # CLI command handlers and config helpers
├── parsers/             # Load test result parsers
├── reporting/           # Markdown/HTML/PDF/JUnit/GitHub reporting
├── services/            # Shared analysis and report orchestration
├── analyzer.py          # Core analysis pipeline + Python API
├── cli.py               # Thin CLI entrypoint
├── comparator.py        # Baseline comparison
├── detector.py          # Anomaly detection
├── kpi.py               # KPI calculations
├── llm.py               # LLM integration
├── loki.py              # Loki client
├── prometheus.py        # Prometheus client
├── setup_llm.py         # LLM setup wizard
├── tempo.py             # Tempo client
└── web.py               # Optional FastAPI app
```

---

## Repository Boundaries

Treat the repository as four zones:

- `heimr/`, `tests/`, `docs/`: primary maintained code and documentation.
- `demos/`, `load-tests/`, `website/`: support surfaces that should consume the package, not define it.
- `.venv/`, `LOCAL/`, `config/`, `build/`, `demos/output/`, `load-tests/results/`: local/generated state that should stay untracked.
- Packaging and automation files at the root (`pyproject.toml`, `action.yml`, `Dockerfile`, `pytest.ini`) should stay small and explicit.

When local artifacts accumulate, clean them with:

```bash
bash scripts/clean_local_artifacts.sh
```

To also remove local runtime directories:

```bash
bash scripts/clean_local_artifacts.sh --include-local
```

---

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Install optional extras only when needed:

```bash
pip install -e .[reports]
pip install -e .[mcp]
pip install -e .[web]
```

---

## Anomaly Detection

### Why NOT Machine Learning?

We evaluated several ML approaches:

**Isolation Forest** (PyOD):

- ❌ Required constant parameter tuning (contamination, threshold)
- ❌ Produced false positives on healthy baselines
- ❌ Black box - hard to explain WHY something is an anomaly

**Specialized Time Series Models** (THEMIS, MAAT, AnomalyBERT):

- ❌ Overkill for simple load test analysis (100 data points)
- ❌ Designed for complex multivariate forecasting (1000s of time steps)
- ❌ Require large training datasets and fine-tuning
- ❌ Deployment complexity (model serving, versioning)

**Verdict**: Simple statistical methods work better for this use case.

### Our Approach: Multi-Signal Statistical Detection

```python
def detect_anomalies(df):
    # Z-Score detection
    mean = df['elapsed'].mean()
    std = df['elapsed'].std()
    threshold = mean + (2.5 * std)
    outliers = df[df['elapsed'] > threshold]
    
    # IQR detection for robustness
    q1, q3 = df['elapsed'].quantile([0.25, 0.75])
    iqr = q3 - q1
    iqr_threshold = q3 + (1.5 * iqr)
    
return outliers
```

### Detector Modes

Heimr supports explainable detector modes via `--detector-mode` or `detector_mode` in `heimr.yaml`:

- `simple` (default): current multi-signal approach (absolute shift, z-score, bimodal tail, degradation tail).
- `mad`: robust MAD outliers for spike detection.
- `trend`: detects slow tail degradation (last 25% slower by `trend_threshold`) plus MAD spikes.

`trend_threshold` is a fraction (default `0.5` = 50% slower tail).

### Why This Works Better

1. **Explainable**: "Latency exceeded mean + 2.5 standard deviations"
2. **No false positives**: Healthy baselines don't trigger
3. **Fast**: O(n) complexity, no model training
4. **No tuning**: Works out of the box
5. **Catches all patterns**:
   - Spikes (statistical outliers)
   - Bimodal distributions (cache misses)
   - Gradual degradation (memory leaks)
   - Errors, high CPU, memory growth

---

## LLM Integration

### Model Tiers

Heimr supports tiered local LLMs:

| Tier | Model | RAM | Use Case |
|------|-------|-----|----------|
| Small | `qwen3.5:4b` | ~3.4GB | CI/CD, laptops |
| Medium | `qwen3.5:9b` | ~6.6GB | Default, 16GB machines |
| Large | `qwen3.5:27b` | ~17GB | Best reasoning, workstations |

**Cloud Options**: OpenAI (GPT-4o) and Anthropic (Claude 3.5 Sonnet) supported.

### Context Stuffing

We compress multi-signal data into a structured prompt:

```python
def construct_prompt(stats, anomalies, prometheus, loki, tempo):
    prompt = f"""
You are a performance engineering expert.

## Test Statistics
- Total Requests: {stats['total_requests']}
- P99 Latency: {stats['p99_latency']:.2f}ms
- Error Rate: {stats['error_rate']:.2f}%

## Detected Anomalies
{format_anomalies(anomalies)}

## Infrastructure Metrics (Prometheus)
{format_prometheus(prometheus)}

## Application Logs (Loki)
{format_loki(loki)}

## Distributed Traces (Tempo)
{format_tempo(tempo)}

Provide root cause analysis with specific evidence.
"""
    return prompt
```

---

## Research & Decisions

### Evaluated Alternatives

#### Traditional ML

| Method | Status | Issue |
|--------|--------|-------|
| Isolation Forest | ❌ Replaced | Parameter tuning, false positives |
| DBSCAN | ❌ Rejected | Not ideal for 1D time series |
| LOF | ❌ Rejected | Slower, similar results |

#### Specialized ML Models

| Model | Status | Issue |
|-------|--------|-------|
| THEMIS | ❌ Rejected | Overkill for load test analysis |
| MAAT | ❌ Rejected | Requires multivariate data |
| AnomalyBERT | ❌ Rejected | Too complex, needs training data |

#### Time Series Methods

ARIMA, Prophet, Seasonal Decomposition - all rejected as overkill for simple load tests.

### Final Decision

**Simple statistical methods + LLM analysis** is optimal:

- ✅ Explainable
- ✅ Fast
- ✅ No false positives
- ✅ No training required
- ✅ Works out of the box

The complexity is in the **integration and correlation**, not the algorithm.

---

## Testing

### Run Tests

```bash
# Unit tests
pytest

# With coverage
pytest --cov=heimr --cov-report=term-missing
```

### Generate Mock Data

```bash
python scripts/generate_mock_data.py
```

### Validate Scenarios

```bash
python scripts/validate_scenarios.py \
  --llm-url http://localhost:11434/v1 \
  --llm-model qwen3.5:9b
```

### Analyze Reports

```bash
python scripts/analyze_reports.py
```

---

## Contributing

See [Contributing Guide](contributing.md) for development setup and contribution guidelines.
