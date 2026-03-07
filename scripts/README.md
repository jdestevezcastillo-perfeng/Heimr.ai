# Development Scripts

Utility scripts for developing and testing Heimr.

## Scripts

### `generate_mock_data.py`
Generates synthetic load test results and observability data for all 140+ failure scenarios.

```bash
python scripts/generate_mock_data.py
```

**Output:** Creates `data/mocks/<SCENARIO_ID>/` directories with:
- `jmeter_results.csv` — JMeter JTL format
- `k6_results.json` — k6 JSON format
- `simulation.log` — Gatling log format
- `locust_stats_history.csv` — Locust CSV format
- `prometheus_metrics.json` — Prometheus metrics snapshot
- `loki_logs.json` — Loki logs snapshot
- `tempo_traces.json` — Tempo traces snapshot

---

### `validate_scenarios.py`
Runs Heimr analysis on all mock scenarios with LLM. Used for full validation.

```bash
# With local Ollama
python scripts/validate_scenarios.py \
  --llm-url http://localhost:11434/v1 \
  --llm-model qwen3.5:9b

# With OpenAI
python scripts/validate_scenarios.py \
  --provider openai \
  --api-key $OPENAI_API_KEY
```

---

### `quick_validate.py`
Fast validation of anomaly detection without LLM. Good for CI/CD.

```bash
python scripts/quick_validate.py
```

**Checks:**
- `API-001` (Healthy Baseline) should `PASS`
- All other scenarios should `FAIL` (anomaly detected)

---

### `analyze_reports.py`
Cross-references generated reports with expected scenario behavior.

```bash
python scripts/analyze_reports.py
```

**Validates:**
- Healthy baselines marked as `PASSED`
- Failure scenarios marked as `FAILED`
- Anomaly counts match expectations

---

### `validate_mock_reports.py`
Deep validation of report content — checks if the right failure patterns are mentioned.

```bash
python scripts/validate_mock_reports.py
```

**Output:** Generates `data/mocks/VALIDATION_SUMMARY.md` with detailed results.

---

## Prerequisites

1. Generate mock data first:
   ```bash
   python scripts/generate_mock_data.py
   ```

2. Have Ollama running (for LLM validation):
   ```bash
   ollama serve
   ollama pull qwen3.5:9b
   ```

## Typical Workflow

```bash
# 1. Generate mock data
python scripts/generate_mock_data.py

# 2. Quick check (no LLM, fast)
python scripts/quick_validate.py

# 3. Full validation (with LLM)
python scripts/validate_scenarios.py --llm-url http://localhost:11434/v1 --llm-model qwen3.5:9b

# 4. Analyze results
python scripts/analyze_reports.py
```
