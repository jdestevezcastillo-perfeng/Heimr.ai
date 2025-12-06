# Heimr.ai Project State - 2025-12-05

**Last Updated:** 2025-12-06T00:05:00+01:00
**Status:** Active Development (Phase: UX Refinement & Feature Completion)
**Current Task:** ✅ DB Span Verification Complete | ✅ Large Tier Model Verified (Qwen 2.5 14B)

## 1. Core Analysis Engine (`heimr/`)
The brain of the operation. Parses load test data, detects anomalies, and uses LLMs for layered analysis.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Parsers** | Started with JTL -> Added k6, Gatling, Locust -> Refined k6 for granular/summary JSON. | **Mature**. Supports all major formats. k6 parser robust to mixed output. | - Support for JMeter CSV (if different from JTL).<br>- Streaming parsing for massive files. |
| **Detector** | Basic threshold detection -> Statistical anomaly detection (Z-score/IQR). | **Stable**. Detects latency spikes effectively. | - Add trend detection (gradual degradation).<br>- Correlate anomalies across multiple metrics. |
| **LLM Integration** | Placeholder -> Local Ollama support -> Enhanced prompts -> **AI-FIRST BY DEFAULT**. | **Excellent**. LLM analysis runs automatically with Ollama/Llama3.1:8b. Full data context (metrics, logs, traces). | - Fine-tune prompts for specific failure scenarios. |
| **Observability Clients** | Basic HTTP requests -> Added Prometheus, Loki, Tempo clients -> **Unified URL/file detection**. | **Robust**. Auto-detects URLs vs file paths. Handles timeouts and empty data gracefully. | - Support for authenticated endpoints (Basic Auth/Bearer). |
| **CLI** | Simple args -> Subcommands -> YAML config -> Comparison -> **MASSIVELY SIMPLIFIED**. | **Excellent**. 41% fewer arguments. AI-first, auto-generated outputs. | - Add batch processing command. |
| **Comparator** | New -> Production-ready -> **Auto-generated alongside reports**. | **Production-Ready**. Automatically creates comparison reports with `_comparison` suffix. | - Add statistical significance testing. |
| **PDF Generator** | **New** -> `heimr/pdf_generator.py` created. | **Production-Ready**. Professional PDFs with custom styling, headers, footers, page numbers. Auto-generated for all markdown reports. | - Add custom branding options. |
| **Dashboard** | Non-existent -> Created -> **Auto-generated**. | **Advanced**. HTML dashboards with Chart.js visualizations. Auto-generated alongside reports. | - Add interactive filtering. |

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
| **README** | Basic -> Feature-rich -> **UPDATED**. | **Excellent**. Reflects all new features: PDF export, auto-generation, simplified CLI, AI-first approach. | - Add video demo. |

## 5. Reporting & Visualization
The face of the results.

| Component | Evolution | Current State | Pending Tasks |
|-----------|-----------|---------------|---------------|
| **Markdown Report** | Simple text -> Structured sections -> Enhanced. | **Excellent**. Includes Business Summary & Per-Endpoint KPI Table. | - Add custom templates. |
| **PDF Report** | **New** -> Auto-generated. | **Production-Ready**. Professional formatting, auto-generated alongside markdown. | - Add custom branding. |
| **HTML Dashboard** | Non-existent -> Created -> **Auto-generated**. | **Advanced**. Grid layout, separate charts, system metrics. Auto-generated alongside reports. | - Add interactive filtering. |
| **Comparison Report** | New -> Integrated -> **Auto-generated**. | **Production-Ready**. Compares baseline vs current with verdict, deltas, and recommendations. Auto-generated with `_comparison` suffix. | - Add trend analysis across multiple runs. |

---

## Recent Changes (2025-12-05)

### Major UX Overhaul - Simplified CLI & AI-First Approach

**Problem**: Too many CLI arguments (17), confusing options, AI analysis was optional.

**Solution**: Massive simplification and paradigm shift:

1.  **PDF Export Feature** (`heimr/pdf_generator.py`):
    *   Auto-generates professional PDFs alongside markdown reports
    *   Custom CSS with headers, footers, page numbers
    *   No separate `--pdf` argument needed

2.  **Auto-Generated Outputs**:
    *   Removed `--pdf` and `--dashboard` arguments
    *   One `--output` creates 3 files: `.md`, `.pdf`, `.html`
    *   Comparison reports auto-generated with `_comparison` suffix

3.  **Unified Observability Arguments**:
    *   Consolidated `--prometheus-url` and `--prometheus-file` into `--prometheus`
    *   Same for `--loki` and `--tempo`
    *   Auto-detects URLs vs file paths

4.  **AI-First by Default** (BREAKING CHANGE):
    *   Removed `--explain` flag
    *   LLM analysis now runs automatically
    *   Default: Ollama at `http://localhost:11434/v1` with `llama3.1:8b`
    *   Added `--no-llm` to disable (rare edge cases)

**Result**: CLI reduced from 17 to 10 arguments (41% reduction). Much more intuitive and powerful.

**Before**:
```bash
heimr analyze results.json --explain \
  --prometheus-url http://localhost:9090 \
  --output report.md \
  --pdf report.pdf \
  --dashboard dashboard.html
```

**Now**:
```bash
heimr analyze results.json \
  --prometheus http://localhost:9090 \
  --output report.md
# Auto-creates: report.md, report.pdf, report.html
# AI analysis runs automatically!
```

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

**Next Step**: Wait for user feedback / Start Grafana Integration.

## Immediate Priorities (Refined Roadmap)
1.  [x] **CI/CD Integration**: Gating, GitHub Actions Summary, JUnit XML.
2.  [ ] **Grafana Integration**: Real-time dashboards.
3.  [ ] **Trend Analysis**: Historical tracking (Low Priority).
