#!/usr/bin/env bash
# The one set of checks. GitHub Actions and the Jenkinsfile both call this, so they cannot drift.
set -euo pipefail

python -m pytest
python -m ruff check .
python -m mypy
