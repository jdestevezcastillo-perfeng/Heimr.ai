# Heimr.ai Project State - 2025-12-05

**Last Updated:** 2025-12-05T20:10:00+01:00
**Status:** Active Development (Phase: Validation & Refinement)

## 1. Core Analysis Engine (`heimr/`)
The brain of the operation. Parses load test data, detects anomalies, and uses LLMs for RCA.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Parsers** | Started with JTL -> Added k6, Gatling, Locust -> Refined k6 for granular/summary JSON. | **Mature**. Supports all major formats. k6 parser robust to mixed output. | - Support for JMeter CSV (if different from JTL).<br>- Streaming parsing for massive files. |
| **Detector** | Basic threshold detection -> Statistical anomaly detection (Z-score/IQR). | **Stable**. Detects latency spikes effectively. | - Add trend detection (gradual degradation).<br>- Correlate anomalies across multiple metrics. |
| **LLM Integration** | Placeholder -> Local Ollama support -> **Enhanced prompts with full data context**. | **Excellent**. Now extracts actual Prometheus stats (avg/min/max/trend), categorizes logs by level, and reports slowest trace spans with operation names. | - Fine-tune prompts for DB query analysis when Tempo has DB spans. |
| **Observability Clients** | Basic HTTP requests -> Added Prometheus, Loki, Tempo clients -> Fixed timeouts & error handling. | **Robust**. Handles timeouts and empty data gracefully. | - Support for authenticated endpoints (Basic Auth/Bearer).<br>- More complex PromQL queries for specific insights. |
| **CLI** | Simple args -> Added subcommands (`analyze`, `config-init`) -> Added YAML config support -> **Added comparison args**. | **User-Friendly**. `--config` and `config-init` make it easy to use. Comparison feature for regression testing. | - Add `dashboard` command for HTML generation. |
| **Comparator** | **New** -> `heimr/comparator.py` created. | **Production-Ready**. Compares metrics, anomalies, Prometheus, logs, and traces. Generates separate comparison report with verdict. | - Add statistical significance testing.<br>- Add comparison visualization. |

## 2. Test Environment (`k8s/`)
The playground for validating Heimr. A complete microservices setup on Minikube.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Observability Stack** | Manual install -> Helm charts -> Custom manifests for Prom/Loki/Tempo/Grafana. | **Complete**. Full stack running in `heimr-test` namespace. Fixed Tempo config. | - Persistent storage (PVCs) for long-term data.<br>- AlertManager integration. |
| **Test Application** | Simple Python script -> FastAPI + Postgres -> Added Chaos Endpoints & OTel + **psycopg2 instrumentation**. | **Advanced**. Includes unindexed table for slow queries, chaos injection (latency, error, leak). DB queries are traced via OTel. | - Ensure Tempo is running during load tests to collect DB spans. |
| **Chaos Injection** | Manual scripts -> `inject-chaos.sh` -> `run-chaos-scenario.sh` automation. | **Automated**. Can run end-to-end chaos scenarios. | - Add network partition chaos.<br>- Add CPU burn chaos. |

## 3. Load Testing (`load-tests/`)
The stress inducers.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Scripts** | Basic k6 script -> Added Locust, JMeter, Gatling -> Refined k6 for granular JSON. | **Comprehensive**. k6 is the primary driver with advanced scenarios. | - Standardize output formats for all tools.<br>- Add distributed load testing support. |
| **Automation** | Manual execution -> `run-integration-test.sh` -> `run-chaos-scenario.sh`. | **Automated**. Single command to run test + chaos + analysis. Uses `heimr-test.yaml` with all observability URLs. | - CI/CD pipeline integration (GitHub Actions). |

## 4. Documentation (`docs/`)
The manual.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Strategy** | Mental model -> `TESTING_STRATEGY.md`. | **Clear**. Defines phases and success criteria. | - Update with latest CLI usage.<br>- Add troubleshooting guide. |
| **Walkthrough** | `task.md` -> `walkthrough.md`. | **Up-to-date**. Guides user through deployment and testing. | - Add screenshots/diagrams. |

## 5. Reporting & Visualization
The face of the results.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Markdown Report** | Simple text -> Structured sections -> **Enhanced**. | **Excellent**. Includes Business Summary & Per-Endpoint KPI Table. | - Add PDF export. |
| **HTML Dashboard** | **Non-existent** -> `heimr/dashboard.py`. | **Advanced**. Grid layout, separate charts, system metrics. | - **Parked**. Future improvements moved to `IDEAS.md` (Grafana). |
| **Comparison Report** | **New** -> Integrated into CLI. | **Production-Ready**. Compares baseline vs current with verdict, deltas, and recommendations. | - Add trend analysis across multiple runs. |

---

## Recent Changes (2025-12-05)

### LLM Prompt Overhaul (`heimr/llm.py`)
**Problem**: LLM was only receiving metadata (e.g., "cpu_usage: 50 data points") instead of actual values, causing it to ask readers to "check CPU metrics manually."

**Solution**: Complete rewrite of `_construct_prompt()` with three new helper methods:
- `_format_prometheus_metrics()`: Extracts avg/min/max/trend for each metric, adds warnings for high CPU or memory growth
- `_format_loki_logs()`: Categorizes by log level, extracts HTTP status codes, shows top error/warning samples
- `_format_tempo_traces()`: Shows duration stats, operation names, HTTP status codes, and **Top 5 Slowest Spans**

**Result**: LLM now receives complete data context to perform accurate RCA.

### Performance Comparison Feature (`heimr/comparator.py`)
**Need**: Regression testing capability to compare current test results against a baseline.

**Implementation**: Created `PerformanceComparator` class with comprehensive comparison logic:
- Compares all key metrics (latency, throughput, errors) with deltas and % changes
- Detects new anomalies between runs
- Compares Prometheus metrics (CPU/memory trends) - shows absolute change in percentage points for clarity
- Compares Loki logs (error/warning counts)
- Compares Tempo traces (identifies new slow operations and regressions)
- Generates separate comparison report with overall verdict (Regression/Improvement/Mixed)
- Provides actionable recommendations based on differences

**Usage**:
```bash
heimr analyze new-test.json \
  --compare-baseline baseline.json \
  --compare-prometheus baseline_prom.json \
  --compare-loki baseline_loki.json \
  --compare-tempo baseline_tempo.json \
  --comparison comparison_report.md
```

**Result**: Production-ready regression testing. Successfully tested - detects new slow DB operations and performance degradations.

### DB Query Tracing
**Finding**: Test app has `Psycopg2Instrumentor().instrument()` so DB queries appear as spans in Tempo traces. However, load tests had `--tempo-url` configured but Tempo wasn't collecting traces during execution.

**Action**: Ensure Tempo pod is running and receiving traces before starting load tests.

---

## Immediate Roadmap
1. ✅ **Refine LLM Prompts**: Done (full data extraction).
2. ✅ **Build Dashboard**: Done (Grid Layout).
3. ✅ **Comparison Feature**: Done (regression testing with separate report).
4. **Next**: Re-run load tests with Tempo collecting to verify DB span visibility.
5. **Future**: Expand chaos scenarios (CPU, Memory), Grafana integration, PDF export.

