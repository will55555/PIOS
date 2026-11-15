#!/usr/bin/env bash
# One entry point for every module (ADR-PIOS-ALGO-009): scripts/task.sh <module> <build|test|lint|run>
# CI keeps calling scripts/check.sh until path-based CI exists.
set -euo pipefail
module="${1:?module: core|algo|compute}"  # the UI lives in the pios-fe repo
action="${2:?action: build|test|lint|run}"

case "$module:$action" in
  core:test)        python -m pytest ;;
  core:lint)        python -m ruff check . && python -m mypy ;;
  algo:build)       uv pip install -e "pios/algo[dev]" ;;
  algo:test)        (cd pios/algo && python -m pytest) ;;
  algo:lint)        (cd pios/algo && python -m ruff check . && python -m mypy) ;;
  compute:build)    cmake -S pios/algo/compute -B build/compute && cmake --build build/compute ;;
  compute:test)     ctest --test-dir build/compute ;;
  *) echo "no '$action' for '$module' yet" >&2; exit 2 ;;
esac
