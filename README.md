# Heimr.ai - AI-Powered Load Test Analysis

Heimr is a CLI tool that analyzes load test results (JMeter, k6, Gatling) and uses LLMs (OpenAI, Anthropic) to explain anomalies and provide root cause analysis.

## Features
- **Multi-Format Support**: Parse JTL (JMeter), JSON (k6), LOG (Gatling), and CSV (Locust).
- **Anomaly Detection**: Detect latency spikes using Isolation Forest.
- **AI Analyst**: Generate natural language explanations for performance issues.
- **Prometheus Integration**: Correlate load test data with system metrics.

## Installation

```bash
git clone https://github.com/heimr-ai/heimr.git
cd heimr
pip install .
```

## Usage

### 1. Analyze Load Test Results
Heimr supports **JMeter (JTL/CSV)**, **k6 (JSON)**, and **Gatling (LOG)**.

```bash
# Analyze a JTL file
heimr analyze results.jtl

# Analyze a k6 JSON file
heimr analyze results.json --format k6

# Analyze a Gatling log
heimr analyze simulation.log --format gatling

# Analyze a Locust CSV (stats_history)
heimr analyze locust_stats_history.csv
```

### 2. AI-Powered Explanation
Get a natural language explanation of anomalies (requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).

```bash
export OPENAI_API_KEY="sk-..."
heimr analyze results.jtl --explain
```

### 3. Prometheus Integration
Correlate anomalies with system metrics.

```bash
heimr analyze results.jtl --prometheus-url http://localhost:9090
```

### 4. Local LLM (Ollama/vLLM)
Use a local inference server compatible with OpenAI API.

```bash
# Example with Ollama running Llama 3
heimr analyze results.jtl --explain \
  --llm-url http://localhost:11434/v1 \
  --llm-model llama3
```

### 5. Docker Usage
Run Heimr without installing Python dependencies.

```bash
docker build -t heimr .
docker run --rm -v $(pwd)/results:/data heimr analyze /data/results.jtl
```

### 6. Release
To build and check the package for PyPI:

```bash
./release.sh
```

## License
Proprietary. All Rights Reserved.
