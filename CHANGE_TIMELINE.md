# Change Timeline

Log of major changes and features added to Heimr.ai.

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
