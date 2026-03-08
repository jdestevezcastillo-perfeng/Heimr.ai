#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/clean_local_artifacts.sh [--include-local]

Cleans generated and local development artifacts from the repository working tree.

By default this removes only common build/test outputs:
  - build/
  - dist/
  - .pytest_cache/
  - .mypy_cache/
  - .coverage
  - htmlcov/
  - heimr_ai.egg-info/
  - demos/output/
  - load-tests/results/

With --include-local it also removes local-only runtime directories:
  - .venv/
  - config/
  - LOCAL/

The script only deletes paths that already exist in the current checkout.
EOF
}

include_local=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--include-local" ]]; then
  include_local=1
elif [[ $# -gt 0 ]]; then
  echo "Unknown argument: $1" >&2
  usage >&2
  exit 1
fi

paths=(
  "build"
  "dist"
  ".pytest_cache"
  ".mypy_cache"
  ".coverage"
  "htmlcov"
  "heimr_ai.egg-info"
  "demos/output"
  "load-tests/results"
)

if [[ $include_local -eq 1 ]]; then
  paths+=(
    ".venv"
    "config"
    "LOCAL"
  )
fi

for path in "${paths[@]}"; do
  if [[ -e "$path" ]]; then
    rm -rf "$path"
    echo "removed $path"
  fi
done
