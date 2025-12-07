# Architecture & Implementation Details

This document contains technical details for developers and contributors.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Anomaly Detection](#anomaly-detection)
3. [LLM Integration](#llm-integration)
4. [Data Pipeline](#data-pipeline)
5. [Research & Decisions](#research--decisions)

---

## System Architecture

### High-Level Flow

```text
Load Test Results → Parser → Anomaly Detector → Multi-Signal Analyzer → LLM → Report
                       ↓            ↓                    ↓
                  Prometheus    Loki Logs          Tempo Traces
```

### Components

1. **Parsers** (`heimr/parsers/`):
   - JMeter (JTL/CSV)
   - k6 (JSON)
   - Gatling (simulation.log)
   - Locust (stats_history.csv)

2. **Anomaly Detector** (`heimr/detector.py`):
   - Multi-signal statistical detection
   - No ML models required
   - Fully explainable

3. **Observability Clients** (`heimr/observability/`):
   - Prometheus: Infrastructure metrics
   - Loki: Application logs
   - Tempo: Distributed traces

4. **LLM Client** (`heimr/llm.py`):
   - Local: Ollama/vLLM (OpenAI-compatible API)
   - Cloud: OpenAI, Anthropic
   - Prompt engineering for performance analysis

5. **Analyzer** (`heimr/analyzer.py`):
   - Core orchestration logic
   - Pipeline management (Parse -> Detect -> AI)
   - Public Python API

6. **CLI** (`heimr/cli.py`):
   - Argument parsing
   - Thin wrapper around Analyzer
   - Report generation

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
def detect_anomalies(df, prometheus_metrics, loki_logs, tempo_traces):
    signals = []
    
    # Signal 1: Statistical outliers
    mean = df['elapsed'].mean()
    std = df['elapsed'].std()
    threshold = mean + (2.5 * std)
    outliers = df[df['elapsed'] > threshold]
    if len(outliers) > 0:
        signals.append(f"Anomalies: {len(outliers)}")
    
    # Signal 2: Bimodal distribution (cache miss pattern)
    p50 = df['elapsed'].quantile(0.50)
    p99 = df['elapsed'].quantile(0.99)
    if p99 > p50 * 2:
        signals.append(f"Bimodal: P99={p99}ms, P50={p50}ms")
    
    # Signal 3: Gradual degradation (memory leak pattern)
    if len(df) >= 20:
        first_20_avg = df.head(20)['elapsed'].mean()
        last_20_avg = df.tail(20)['elapsed'].mean()
        if last_20_avg > first_20_avg * 1.5:
            signals.append(f"Degradation: {(last_20_avg/first_20_avg - 1)*100:.1f}% slower")
    
    # Signal 4: Error rate
    error_rate = (df['success'] == False).sum() / len(df) * 100
    if error_rate > 0:
        signals.append(f"Error Rate: {error_rate:.2f}%")
    
    # Signal 5: High CPU (from Prometheus)
    if prometheus_metrics and 'cpu_usage' in prometheus_metrics:
        cpu_values = [float(v[1]) for v in prometheus_metrics['cpu_usage'][0]['values']]
        avg_cpu = sum(cpu_values) / len(cpu_values)
        if avg_cpu > 0.8:
            signals.append(f"High CPU: {avg_cpu*100:.1f}%")
    
    # Signal 6: Memory growth (from Prometheus)
    if prometheus_metrics and 'memory_usage' in prometheus_metrics:
        mem_values = [int(v[1]) for v in prometheus_metrics['memory_usage'][0]['values']]
        if len(mem_values) >= 2:
            mem_growth = (mem_values[-1] - mem_values[0]) / mem_values[0]
            if mem_growth > 0.5:
                signals.append(f"Memory Growth: {mem_growth*100:.1f}%")
    
    # Signal 7: Error/Warn logs (from Loki)
    if loki_logs:
        error_count = sum(1 for log in loki_logs if 'level=error' in log or 'level=warn' in log)
        if error_count > 0:
            signals.append(f"Error/Warn Logs: {error_count}")
    
    # Signal 8: Slow traces (from Tempo)
    if tempo_traces:
        signals.append(f"Slow Traces: {len(tempo_traces)}")
    
    return signals
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

### LLM Strategy & Model Tiers

Heimr supports a tiered approach to local LLMs to accommodate different hardware capabilities:

**1. Small Tier** (`llama3.2:3b`)

- **Target**: Laptops with <8GB RAM, CI/CD pipelines
- **Pros**: Extremely fast, low memory (~2GB)
- **Cons**: Limited reasoning, concise outputs

**2. Medium Tier** (`llama3.1:8b`) - **DEFAULT**

- **Target**: Standard dev machines (16GB RAM)
- **Pros**: Good balance of instruction following and speed (~5GB)
- **Cons**: Can struggle with complex multi-signal correlation

**3. Large Tier** (`qwen2.5:14b`)

- **Target**: Workstations (16GB-24GB RAM allowed)
- **Selection**: Chosen over Llama 3.1 70B (which requires ~40GB RAM)
- **Pros**: Superior reasoning, "Small but Mighty" performance (~9GB)
- **Cons**: Slower generation speed

**Cloud Options**: OpenAI (GPT-4o) and Anthropic (Claudia 3.5 Sonnet) are supported for users without local GPU capability.

### Prompt Engineering

The key to good LLM analysis is **structured prompts**:

```python
def construct_prompt(stats, anomalies, prometheus, loki, tempo):
    prompt = f"""
You are a performance engineering expert analyzing load test results.

## Test Statistics
- Total Requests: {stats['total_requests']}
- Average Latency: {stats['avg_latency']:.2f}ms
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

## Task
Provide a comprehensive root cause analysis:
1. Executive Summary (2-3 sentences)
2. Detailed Analysis (what patterns do you see?)
3. Anomaly Investigation (correlate anomalies with metrics/logs/traces)
4. Potential Root Causes (ranked by likelihood)
5. Recommendations (specific, actionable steps)

Be technical but clear. Cite specific evidence from the data.
"""
    return prompt
```

### Future: Fine-Tuning

We plan to fine-tune Llama 3 on performance analysis tasks:

**Training Data**:

- 156 failure scenarios
- Load test results → Root cause analysis pairs
- Real-world incident reports (anonymized)

**Expected Improvement**:

- More accurate root cause identification
- Better correlation across signals
- Domain-specific terminology

---

## Data Pipeline

### Mock Data Generation

For testing and validation, we generate scenario-specific mock data:

**Load Test Results**:

- Healthy: Tight latency distribution (100-120ms)
- Latency Spike: 10% extreme outliers (3-5s)
- Bimodal: 40% slow (3-5s), 60% fast (80-150ms)
- Memory Leak: Gradual increase (100ms → 3000ms)
- CPU Saturation: Sudden spike after warmup

**Observability Data**:

- Prometheus: Scenario-specific CPU/memory patterns
- Loki: Relevant error messages (cache miss, GC pause, etc.)
- Tempo: Detailed span breakdowns showing root causes

**156 Scenarios** covering:

- API issues (latency, errors, rate limiting)
- Infrastructure (OOM, CPU, network)
- Database (slow queries, deadlocks)
- Cache (stampede, avalanche, penetration)
- And many more...

---

## Research & Decisions

### Evaluated Alternatives

#### 1. Specialized ML Models

**THEMIS** (HuggingFace):

- Foundation model for time series anomaly detection
- Pre-trained on Chronos dataset
- **Verdict**: Overkill for load test analysis

**MAAT** (Mamba-SSM):

- State-of-the-art for multivariate time series
- **Verdict**: Requires multivariate data (we have univariate latency)

**AnomalyBERT**:

- BERT-based time series anomaly detection
- **Verdict**: Too complex, requires large training datasets

#### 2. Traditional ML

**Isolation Forest**:

- Initially used
- **Issues**: Parameter tuning, false positives
- **Replaced with**: Simple statistical methods

**DBSCAN**:

- Density-based clustering
- **Verdict**: Not ideal for 1D time series

**LOF** (Local Outlier Factor):

- Measures local density deviation
- **Verdict**: Slower than needed, similar results to simpler methods

#### 3. Time Series Methods

**ARIMA, Prophet, Seasonal Decomposition**:

- **Verdict**: Overkill for simple load tests, assumes temporal ordering

### Final Decision

**Simple statistical methods + LLM analysis** is the optimal approach:

- ✅ Explainable
- ✅ Fast
- ✅ No false positives
- ✅ No training required
- ✅ Works out of the box

The complexity is in the **integration and correlation**, not the algorithm.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

### Code Structure

```text
heimr/
├── parsers/          # Load test result parsers
│   ├── jtl.py       # JMeter
│   ├── k6.py        # k6
│   ├── gatling.py   # Gatling
│   └── locust.py    # Locust
├── observability/    # Observability integrations
│   ├── prometheus.py
│   ├── loki.py
│   └── tempo.py
├── detector.py       # Anomaly detection
├── llm.py           # LLM integration
├── analyzer.py      # Core Analysis Pipeline
└── cli.py           # CLI interface
```

### Testing

```bash
# Run tests
pytest

# Generate mock data
python scripts/generate_mock_data.py

# Validate all scenarios
python scripts/validate_scenarios.py --llm-url http://localhost:11434/v1 --llm-model llama3.1:8b

# Analyze reports
python scripts/analyze_reports.py
```

---

## License

AGPL v3. See [LICENSE](./LICENSE) for details.
