```text
                                               
   ▄▄▄  ▄▄▄                                    
  █▀██  ██                                     
    ██  ██         ▀▀ ▄        ▄             ▀▀
    ██████   ▄█▀█▄ ██ ███▄███▄ ████▄   ▄▀▀█▄ ██
    ██  ██   ██▄█▀ ██ ██ ██ ██ ██      ▄█▀██ ██
  ▀██▀  ▀██▄▄▀█▄▄▄▄██▄██ ██ ▀█▄█▀  ██ ▄▀█▄██▄██
                                               
                                               
```

# Heimr.ai

**AI-Powered Load Test Analysis & Root Cause Explanation**

Heimr is a command-line tool that transforms raw load test data into actionable insights. It parses results from industry-standard tools, detects statistical anomalies, and uses Large Language Models (LLMs) to generate natural language explanations for performance regressions.

---

## 🚀 Features

*   **Multi-Format Support**: Seamlessly parse and analyze results from:
    *   **JMeter** (`.jtl`, CSV)
    *   **k6** (JSON output)
    *   **Gatling** (`simulation.log`)
    *   **Locust** (`_stats_history.csv`)
*   **Smart Anomaly Detection**: Uses **Isolation Forest** (unsupervised learning) to automatically identify latency spikes and error rate deviations without manual thresholding.
*   **AI Analyst**: Integrates with **OpenAI**, **Anthropic**, and **Local LLMs** (via Ollama/vLLM) to explain *why* performance degraded, correlating anomalies with test statistics.
*   **Prometheus Integration**: Fetches infrastructure metrics (CPU, Memory) during the test window to provide context-aware Root Cause Analysis.
*   **Portable**: Runs as a Python CLI or Docker container.

---

## 📦 Installation

```bash
git clone https://github.com/heimr-ai/heimr.git
cd heimr
pip install .
```

---

## 🛠️ Usage

### 1. Basic Analysis
Analyze a load test file to get a statistical summary and anomaly report.

```bash
# Auto-detects format (JTL, JSON, LOG, CSV)
heimr analyze results.jtl
```

### 2. AI-Powered Explanation (`--explain`)
Generate a natural language report describing the performance issues.

**Using OpenAI / Anthropic:**
```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."

heimr analyze results.jtl --explain
```

**Using Local LLM (Ollama):**
Run completely offline with your own hardware!
```bash
# Assuming Ollama is running on localhost:11434
heimr analyze results.jtl --explain \
  --llm-url http://localhost:11434/v1 \
  --llm-model llama3
```

### 3. Report Generation (`--output`)
Save the full analysis and AI report to a Markdown file.

```bash
heimr analyze results.jtl --explain --output report.md
```

### 4. Prometheus Integration
Correlate application performance with system health.
```bash
heimr analyze results.jtl --prometheus-url http://localhost:9090
```

---

## 🎬 Demos

We have included ready-to-run demo scripts in the `demos/` directory:

*   **Local LLM**: `./demos/demo_local_llm.sh` (Requires Ollama)
*   **Anthropic**: `./demos/demo_anthropic.sh` (Requires API Key)

---

## 🐳 Docker Support

Run Heimr without installing Python dependencies.

```bash
docker build -t heimr .
docker run --rm -v $(pwd)/results:/data heimr analyze /data/results.jtl
```

---

## 🤝 Contributing

1.  Install dependencies: `pip install -r requirements_heimr.txt`
2.  Run tests: `pytest`
3.  Build package: `./release.sh`

---

## License

Proprietary. All Rights Reserved.
