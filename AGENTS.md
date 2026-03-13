# Repository Guidelines

## Project Structure & Module Organization
`heimr/` contains the Python package and core runtime. Key areas include `heimr/agent/` for autonomous workflows, `heimr/commands/` for CLI/config helpers, `heimr/parsers/` for load-test input formats, and `heimr/reporting/` for report generation. Tests live in `tests/`, with reusable sample inputs in `tests/fixtures/`. Supporting assets are split by purpose: `docs/` for the wiki, `scripts/` for validation utilities, `load-tests/` for benchmark tooling, `demos/` for runnable examples, and `website/` for the project site.

## Build, Test, and Development Commands
Create an isolated environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Use `pytest` for the full test suite. CI currently runs `pytest tests/ -v --ignore=tests/validate_outputs.py`. Run coverage with `pytest --cov=heimr --cov-report=html`. Linting is lightweight in CI: `flake8 heimr/ --count --select=E9,F63,F7,F82 --show-source --statistics`. Format and import-sort locally with `black heimr tests` and `isort heimr tests`. For scenario validation, use `python scripts/quick_validate.py` or `python scripts/validate_scenarios.py --llm-url http://localhost:11434/v1 --llm-model qwen3.5:9b`.

## Coding Style & Naming Conventions
Use 4-space indentation, Python type hints where practical, and short module-level docstrings/comments only when they add context. Follow existing naming: `snake_case` for functions, variables, and modules; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants. Keep parser-specific logic inside `heimr/parsers/` and reporting concerns inside `heimr/reporting/`.

## Testing Guidelines
`pytest.ini` enforces `tests/` as the test root and `test_*.py` naming. Match the repository pattern: one test module per feature area, for example `tests/test_prometheus.py` or `tests/test_react_loop.py`. Add fixtures or sample payloads under `tests/fixtures/` when behavior depends on external formats. Cover both happy-path parsing and regression cases around failures, anomaly detection, and CLI behavior.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commits such as `docs: add FAQ section` and `docs: rewrite documentation`. Follow the same `type: summary` format, for example `fix: handle missing Loki response`. Pull requests should include a short problem statement, the implementation scope, test evidence, and screenshots only when UI or website output changes. Link related issues and call out breaking changes explicitly.
