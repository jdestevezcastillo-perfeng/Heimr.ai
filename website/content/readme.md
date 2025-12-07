```text
 █████   █████           ███                           
░░███   ░░███           ░░░                            
 ░███    ░███   ██████  ████  █████████████   ████████ 
 ░███████████  ███░░███░░███ ░░███░░███░░███ ░░███░░███
 ░███░░░░░███ ░███████  ░███  ░███ ░███ ░███  ░███ ░░░ 
 ░███    ░███ ░███░░░   ░███  ░███ ░███ ░███  ░███     
 █████   █████░░██████  █████ █████░███ █████ █████    
░░░░░   ░░░░░  ░░░░░░  ░░░░░ ░░░░░ ░░░ ░░░░░ ░░░░░     
```

# Heimr.ai

**AI-Powered Load Test Analysis & Root Cause Explanation**

Stop staring at charts. Let AI explain what went wrong and how to fix it.

---

## Why Heimr?

### 🎯 Explainable by Design

Unlike black-box ML tools, Heimr shows you **exactly** why something was flagged:

- "P99 latency is 3.2x higher than P50 (bimodal distribution detected)"

- "Memory usage increased 950% during test execution"

- "Cache hit rate dropped to 12%, causing database saturation"

No guessing. No magic. Just clear, actionable insights.

### 🔍 Multi-Signal Intelligence

Heimr doesn't just look at latency. It correlates:

- ✅ Load test anomalies (spikes, bimodal patterns, gradual degradation)

- ✅ Infrastructure metrics (CPU, memory, disk I/O)

- ✅ Application logs (errors, warnings, GC pauses)

- ✅ Distributed traces (slow spans, service dependencies)

- ✅ Error rates and response codes

**140+ failure scenarios** built-in, from cache stampedes to memory leaks.

### 🤖 LLM-Powered Root Cause Analysis

After detecting issues, Heimr uses Large Language Models to:



- Explain the root cause in plain English

- Suggest specific remediation steps

- Correlate patterns across multiple signals

- Generate executive summaries for stakeholders

**Privacy-first**: Run completely local with Llama 3.1 (no data leaves your infrastructure).

### ⚡ Works with Your Stack

Seamless integration with industry-standard tools:

- **Load Testing**: JMeter, k6, Gatling, Locust

- **Metrics**: Prometheus, Grafana

- **Logs**: Loki, Elasticsearch

- **Traces**: Tempo, Jaeger

No vendor lock-in. Use what you already have.

---

## 📚 Documentation

**[→ Full Documentation](docs/WIKI.md)** — Quick Start, CLI Reference, Configuration, AI Engine, Python API, CI/CD, Troubleshooting, and more.

---

## 🚀 Quick Start

### Installation

```bash
pip install heimr-ai

# Install Ollama for local AI analysis (recommended)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
```

### Basic Analysis

```bash
# Analyze any load test result
# AI analysis runs automatically!
heimr analyze results.jtl --output report.md

# Creates 2 files automatically:
# - report.md (Markdown report)
# - report.pdf (PDF version)
```

### With Full Observability

```bash
heimr analyze results.jtl \
  --prometheus http://localhost:9090 \
  --loki http://localhost:3100 \
  --tempo http://localhost:3200 \
  --output report.md

# Or use file paths instead of URLs:
heimr analyze results.jtl \
  --prometheus ./metrics.json \
  --loki ./logs.json \
  --tempo ./traces.json \
  --output report.md
```

### Using a Config File

Instead of specifying all options on the command line, you can use a YAML config file:

```bash
# Generate template config
heimr config-init

# Use config file (CLI args override config values)
heimr analyze results.jtl --config heimr.yaml
```

Example `heimr.yaml`:

```yaml
# Observability sources (URL or file path)
prometheus: http://localhost:9090
loki: http://localhost:3100
tempo: http://localhost:3200

# LLM configuration (defaults shown)
llm_url: http://localhost:11434/v1  # Ollama
llm_model: llama3.1:8b

# Output
output: ./reports/analysis.md

# Comparison (optional)
compare_baseline: ./baseline/results.json
compare_prometheus: ./baseline/metrics.json
```

See `heimr.yaml.example` for the full template with all options.

**Result**: Two comprehensive reports automatically generated:

1. **Markdown Report** (`report.md`):
   - Statistical summary (P50, P95, P99, error rate)
   - Detected anomalies with timestamps
   - Infrastructure correlation (CPU spikes, memory leaks)
   - Log analysis (error patterns, warnings)
   - Trace analysis (slow spans, bottlenecks)
   - **AI-generated root cause explanation and recommendations**

2. **PDF Report** (`report.pdf`):
   - Professional formatting with headers and page numbers
   - Suitable for stakeholder presentations
   - Automatically generated alongside markdown

### Comparison Reports

Compare current results against a baseline for regression testing:

```bash
heimr analyze current.json \
  --compare-baseline baseline.json \
  --compare-prometheus baseline_metrics.json \
  --output report.md

# Creates additional comparison files:
# - report_comparison.md
# - report_comparison.pdf
```

---

## 🎬 See It In Action

### Example Report Output

```markdown
# ❌ FAILED
**Reasons**: Anomalies: 7, Memory Growth: 950%, Error/Warn Logs: 4

## Executive Summary
The load test revealed a critical memory leak causing gradual performance 
degradation. Average latency increased from 100ms to 3000ms over the test 
duration, with 7 anomalous spikes detected.

## Root Cause Analysis
1. **Memory Leak**: Heap usage grew from 100MB to 1GB (950% increase)
2. **GC Pressure**: Frequent garbage collection pauses (up to 5 seconds)
3. **Database Saturation**: Connection pool exhausted due to leaked connections

## Recommendations
1. Review connection pool management in `DatabaseClient.java`
2. Implement connection leak detection with HikariCP
3. Add heap dump analysis to identify leak source
4. Increase monitoring for connection pool metrics
```

---

## 🔐 Privacy & Security

### Run Completely Local

No data ever leaves your infrastructure:

- **Local LLM**: Use Llama 3.1 via Ollama (no API calls)

- **On-premise**: All analysis runs on your hardware

- **Offline**: Works without internet connectivity

### Optional Cloud LLMs

For enhanced analysis, optionally use:

- OpenAI ChatGPT-5.1

- Anthropic Claude Sonnet 4.5

**You control** where your data goes.

---

## 🏢 Enterprise Features


- **Batch Analysis**: Process hundreds of test results in parallel

- **Historical Trending**: Track performance degradation over time

- **Custom Scenarios**: Add your own failure patterns

- **CI/CD Integration**: Automated analysis in your pipeline

- **Team Collaboration**: Share reports and insights

- **SSO/RBAC**: Enterprise authentication and access control

*Contact us for enterprise licensing and support.*

---

## 📊 Supported Failure Scenarios

Heimr recognizes **140+ common failure patterns**, including:

**Performance Issues**:

- Latency spikes (tail latency)

- Bimodal distributions (cache misses)

- Gradual degradation (memory leaks)

- CPU saturation

- Thread starvation

**Infrastructure**:

- OOMKills

- CPU throttling

- Disk I/O saturation

- Network packet loss

- DNS latency

**Application**:

- Database slow queries

- Connection pool exhaustion

- Cache stampedes

- Message queue lag

- Distributed deadlocks

**And many more...**

---

## 🛠️ Advanced Usage

### Custom Prompts

Fine-tune LLM analysis for your domain:

```bash
heimr analyze results.jtl \
  --prompt-template custom_prompt.txt
```

### Programmatic API

```python
from heimr import Analyzer

config = {'prometheus': 'http://localhost:9090'}

analyzer = Analyzer(
    file_path="results.jtl",
    config=config,
    llm_model="llama3.1:8b"
)

result = analyzer.analyze()
print(result.status)
print(result.kpi)
print(result.llm_explanation)
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

For technical implementation details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🌟 Why "Heimr"?

In Norse mythology, **Heimdallr** (Heimr) is the all-seeing guardian who watches over the Bifrost bridge. Like its namesake, Heimr.ai watches over your performance tests, detecting issues before they reach production.

# License

Heimr is licensed under the **GNU Affero General Public License v3 (AGPL v3)**. 

## Open Source Usage

You are free to use, modify, and distribute Heimr under the terms of the AGPL v3 license, provided that:

- Any modifications or derivative works you create are also licensed under AGPL v3
- If you run Heimr as a network service (including SaaS offerings), you must make your modified source code available to your users
- You retain all copyright notices and license information

For the full license text, see [LICENSE](./LICENSE).

## Commercial Licensing

If you intend to use Heimr in a commercial product or service without open-sourcing your modifications, **you are required to obtain a commercial license** from the Heimr authors.

Commercial licensing allows you to:
- Integrate Heimr into proprietary applications
- Distribute Heimr without copyleft obligations
- Keep your modifications and derivative works private
- Use Heimr in closed-source SaaS offerings

### Obtaining a Commercial License

Please contact us to discuss commercial licensing options:

- Email: [jd.estevezcastillo@gmail.com]
- For inquiries: [http://heimr.ai/contact/]

We're flexible on licensing terms and happy to work with businesses of all sizes. Typical arrangements include:
- One-time perpetual licenses
- Deployment-based pricing
- Revenue-share agreements
- Custom terms based on your specific use case

---

## Summary

| Use Case | License Required |
|----------|------------------|
| Open source project using Heimr | AGPL v3 (free) |
| Internal company use (non-public) | AGPL v3 (free) |
| SaaS/web service offering | Commercial License |
| Proprietary product integration | Commercial License |
| Educational/research use | AGPL v3 (free) |
| Modification and private redistribution | AGPL v3 (free) |

If you're unsure whether your use case requires a commercial license, please reach out—we'd rather clarify than have legal surprises down the road.
