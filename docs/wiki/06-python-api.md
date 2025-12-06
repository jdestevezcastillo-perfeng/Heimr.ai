# Python API

[← Back to Index](../WIKI.md)

Heimr can be used programmatically as a Python library, giving you full control over the analysis pipeline.

---

## Installation

```bash
pip install heimr-ai
```

---

## Basic Usage

```python
from heimr import Analyzer

# Initialize with a load test file
analyzer = Analyzer(
    file_path="results.jtl",
    prometheus_url="http://localhost:9090",
    loki_url="http://localhost:3100",
    tempo_url="http://localhost:3200",
    llm_model="llama3.1:8b"
)

# Run analysis
report = analyzer.analyze()

# Access results
print(report.summary)           # Executive summary
print(report.kpis)              # KPI metrics dict
print(report.anomalies)         # List of detected anomalies
print(report.root_causes)       # AI-generated root causes
print(report.recommendations)   # Suggested fixes
```

---

## Configuration Options

### Analyzer Constructor

```python
analyzer = Analyzer(
    # Required
    file_path: str,              # Path to load test results
    
    # Observability (optional)
    prometheus_url: str = None,  # Prometheus URL or file path
    loki_url: str = None,        # Loki URL or file path
    tempo_url: str = None,       # Tempo URL or file path
    
    # LLM Configuration
    llm_url: str = "http://localhost:11434/v1",
    llm_model: str = "llama3.1:8b",
    no_llm: bool = False,        # Skip AI analysis
    
    # Output
    output_path: str = "report.md",
)
```

### Environment Variables

For cloud LLMs, set these before creating the Analyzer:

```python
import os

# OpenAI
os.environ["OPENAI_API_KEY"] = "sk-..."

# Anthropic
os.environ["ANTHROPIC_API_KEY"] = "sk-..."
```

---

## Report Object

The `analyze()` method returns a `Report` object with the following attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `summary` | `str` | Executive summary (AI-generated) |
| `verdict` | `str` | "PASSED" or "FAILED" |
| `kpis` | `dict` | Performance metrics (p50, p95, p99, error_rate, rps) |
| `anomalies` | `list[Anomaly]` | Detected anomaly objects |
| `metrics` | `dict` | Raw Prometheus metrics |
| `logs` | `list[LogEntry]` | Relevant log entries from Loki |
| `traces` | `list[Trace]` | Slow traces from Tempo |
| `root_causes` | `list[str]` | AI-identified root causes |
| `recommendations` | `list[str]` | AI-suggested fixes |

---

## Accessing Anomalies

```python
for anomaly in report.anomalies:
    print(f"Type: {anomaly.type}")
    print(f"Timestamp: {anomaly.timestamp}")
    print(f"Endpoint: {anomaly.endpoint}")
    print(f"Severity: {anomaly.severity}")
    print(f"Description: {anomaly.description}")
```

---

## Generating Reports Programmatically

```python
# Generate Markdown
report.to_markdown("output/report.md")

# Generate PDF
report.to_pdf("output/report.pdf")

# Get raw markdown as string
md_content = report.as_markdown()
```

---

## Comparison Analysis

Compare current results against a baseline:

```python
from heimr import Analyzer, compare_reports

# Analyze current run
current = Analyzer(file_path="current.jtl").analyze()

# Analyze baseline
baseline = Analyzer(file_path="baseline.jtl").analyze()

# Compare
diff = compare_reports(current, baseline)

print(diff.regression_percentage)  # % change
print(diff.degraded_endpoints)     # List of slower endpoints
print(diff.improved_endpoints)     # List of faster endpoints
```

---

## Integration Example: CI/CD

```python
import sys
from heimr import Analyzer

analyzer = Analyzer(
    file_path="results.json",
    no_llm=True  # Fast mode for CI
)

report = analyzer.analyze()

# Check thresholds
if report.kpis["p99_latency"] > 500:
    print("❌ P99 latency exceeds 500ms!")
    sys.exit(1)

if report.kpis["error_rate"] > 1.0:
    print("❌ Error rate exceeds 1%!")
    sys.exit(1)

print("✅ All checks passed")
sys.exit(0)
```

---

## Custom Prompt Templates

For advanced use cases, you can provide custom prompts:

```python
custom_prompt = """
You are a database performance specialist.
Focus your analysis on:
- Query patterns
- Connection pool behavior
- Lock contention

Context:
{context}

Provide your analysis in the following format:
1. Database-specific issues
2. Query optimization recommendations
3. Connection pool tuning suggestions
"""

analyzer = Analyzer(
    file_path="results.jtl",
    prompt_template=custom_prompt
)
```

---

## Error Handling

```python
from heimr import Analyzer, HeimrtError, ParserError, LLMConnectionError

try:
    analyzer = Analyzer(file_path="results.jtl")
    report = analyzer.analyze()
except ParserError as e:
    print(f"Failed to parse file: {e}")
except LLMConnectionError as e:
    print(f"LLM unavailable: {e}")
except HeimrtError as e:
    print(f"Analysis failed: {e}")
```
