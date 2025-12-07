# Development Guide

[← Back to Index](../WIKI.md)

Technical details for developers and contributors.

---

## Table of Contents

1. [Code Structure](#code-structure)
2. [Anomaly Detection](#anomaly-detection)
3. [LLM Integration](#llm-integration)
4. [Research & Decisions](#research--decisions)
5. [Testing](#testing)

---

## Code Structure

```text
heimr/
├── parsers/              # Load test result parsers
│   ├── __init__.py
│   ├── base.py          # Base parser class
│   ├── jtl.py           # JMeter
│   ├── k6.py            # k6
│   ├── gatling.py       # Gatling
│   ├── locust.py        # Locust
│   └── har.py           # HAR files
├── reporters/            # Output formatters
│   ├── github.py        # GitHub Actions integration
│   └── junit.py         # JUnit XML output
├── __init__.py          # Package exports (Analyzer, AnalysisResult)
├── analyzer.py          # Core Analysis Pipeline + Python API
├── cli.py               # CLI interface
├── comparator.py        # Baseline comparison
├── detector.py          # Anomaly detection (Z-Score, IQR)
├── kpi.py               # KPI calculations
├── llm.py               # LLM integration (Ollama, OpenAI, Anthropic)
├── loki.py              # Loki client
├── pdf_generator.py     # PDF report generation
├── prometheus.py        # Prometheus client
├── setup_llm.py         # LLM setup wizard
└── tempo.py             # Tempo client
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
| Small | `llama3.2:3b` | ~2GB | CI/CD, laptops |
| Medium | `llama3.1:8b` | ~5GB | Default, 16GB machines |
| Large | `qwen2.5:14b` | ~9GB | Best reasoning, workstations |

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
  --llm-model llama3.1:8b
```

### Analyze Reports

```bash
python scripts/analyze_reports.py
```

---

## Contributing

See [CONTRIBUTING.md](https://github.com/jdestevezcastillo-perfeng/Heimr.ai/blob/main/CONTRIBUTING.md) for development setup and contribution guidelines.
