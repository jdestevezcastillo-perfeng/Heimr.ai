# Change Timeline

Log of major changes and features added to Heimr.ai.

## 2026-03-08 01:00 CET
- **LLM Model Migration** — Upgraded default local models from Llama 3.x / Qwen 2.5 to Qwen 3.5 family.
  - New tiers: `qwen3.5:4b` (small, ~3.4GB), `qwen3.5:9b` (medium, default, ~6.6GB), `qwen3.5:27b` (large, ~17GB).
  - Updated across all source code, configs, Docker files, demo scripts, docs, wiki, website, tests, and README.
  - Zero remaining references to llama3.x or qwen2.5. All 130 tests pass.

## 2026-03-08 00:15 CET
- **Docker Quickstart (Phase 3)** — End-to-end containerized demo environment.
  - New `docker-compose.quickstart.yml`: 4-service stack (demo-server, Ollama, k6, heimr-agent) with health checks and dependency ordering.
  - New `deploy/entrypoint-quickstart.sh`: Waits for Ollama/results, falls back to sample data on timeout.
  - New `load-tests/k6/quickstart.js`: 1-minute weighted load test (users, products, orders, slow endpoint).
  - New `.env.example`: Documents all configurable variables (model, gate policy, k6 settings).
  - Updated `demos/README.md` with Docker quickstart instructions.
  - Fixed `analyzer.py` None-coalescing bug in `trend_threshold` config.
  - Docker build verified, compose config validated. All 130 tests pass.

## 2026-03-07 23:30 CET
- **MCP Integration (Phase 2)** — Exposed all agent capabilities via Model Context Protocol (MCP).
  - New `heimr/agent/mcp_server.py`: FastMCP server with 8 tools, 2 resources (`heimr://tools`, `heimr://supported-formats`), 2 prompt templates (`analyze_load_test`, `deployment_gate`).
  - Supports stdio transport (Claude Desktop / Claude Code) and streamable-http (remote clients).
  - New CLI subcommand: `heimr mcp --transport stdio|streamable-http --port 8000`.
  - `setup.py` updated with optional `mcp` extra (`pip install heimr[mcp]`).
  - 17 MCP tests (mocked FastMCP import, tool delegation, resources, prompts, CLI handler). All 130 tests pass, zero regressions.

## 2026-03-07 21:10 CET
- **PIVOT: Agent Foundation (Phase 1)** — Transformed Heimr from CLI tool to autonomous performance engineering agent.
  - New `heimr/agent/` package: ReAct loop (`react_loop.py`), 8-tool registry (`tools.py`), deployment gate engine (`gate.py`), agent config (`config.py`).
  - New CLI subcommand: `heimr agent <file>` with `--mode`, `--gate-policy`, `--max-iterations`, `--verbose` flags.
  - New `action.yml` for GitHub Actions marketplace integration.
  - 32 new tests (tools, ReAct loop, gate decisions). All 113 tests pass, zero regressions.
  - Existing `heimr analyze` CLI preserved — fully backward compatible.

## 2025-12-12 00:47 CET
- P3.2: Grafana integration — added `grafana_url`/`grafana_dashboard_uid` config and CLI flags; reports now include a Grafana dashboard link scoped to the test window. Demo docs updated.

## 2025-12-12 00:43 CET
- P3.1: CI/CD polish — wired `--ci-summary` and `--junit-output` into CLI, upgraded GitHub summary to traffic-light format with artifact listing, and ensured tags propagate into CI outputs.

## 2025-12-12 00:40 CET
- P2.3: Split CLI helpers into `heimr/commands/config.py` and reporting helpers into `heimr/reporting/markdown.py`; `heimr/cli.py` re-exports them for backward compatibility.

## 2025-12-12 00:32 CET
- P2.2: Added detector modes via `detector_mode`/`--detector-mode`: `simple`, `mad` (robust spikes with z-score fallback), and `trend` (tail degradation + MAD spikes).
- Anomalies now carry an `anomaly_reason` field for explainability.

## 2025-12-12 00:23 CET
- P2.1: Parsers now preserve raw columns alongside unified schema (`keep_extra=True`).
- Added per-endpoint KPIs (`kpi.per_endpoint`) and per-endpoint anomaly summaries in analysis results.
- Reports and LLM prompts include top slow/erroring endpoints and a per-endpoint KPI table.

## 2025-12-12 00:03 CET
- Added configurable multi-signal thresholds (`cpu_threshold`, `mem_growth_threshold`, `anomaly_threshold`, `error_rate_threshold`) and single-run `fail_conditions` gating.
- Shared failure-condition parser/evaluator via `heimr/failures.py`; comparator now reuses it.
- Baseline comparison gating now affects exit code and reports.
- LLM consistency and reliability: Anthropic honors `llm_model`, added `llm_timeout_sec` and `llm_max_retries`, and unified retry/timeout behavior across providers.
- Converted internal warnings/errors to `logging` in Analyzer and observability clients; added CLI `--log-level`.
- Updated CI/CD and configuration docs and added tests for new gating.

## 2025-12-11 23:52 CET
- Canonicalized config schema: added `normalize_config`, introduced `disable_llm`, mapped legacy `explain`/`no_llm`, and auto-normalized `llm_url` to `/v1`.
- Updated `config-init` output to match canonical `heimr.yaml.example` (tiers, `/v1` URL).
- Deprecated `--explain` flag (warning only); AI analysis now default.
- Analyzer now respects `disable_llm`, normalizes `llm_url`, and includes `error_count` in `stats`.
- Fixed package version export via `importlib.metadata` and removed tracked `dist/` artifacts.
- Removed `requirements.txt`; runtime deps now live in `setup.py`.
- Updated demos, docs, fixtures, and tests to align with the new schema.

## 2025-12-11 23:15 CET
- Added `CHANGE_TIMELINE.md` to track major repo changes over time.
