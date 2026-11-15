#!/usr/bin/env bash
# Set up pios-algo on Linux or macOS, or check an existing setup.
#   --check    report what is missing; install nothing
#   --upgrade  also upgrade packages to the newest versions pyproject.toml allows
# Installs or updates to the latest: uv and a C++ compiler. Python comes from .python-version.
set -euo pipefail
cd "$(dirname "$0")/.."

check=0
upgrade=0
for a in "$@"; do
  case "$a" in
    --check) check=1 ;;
    --upgrade) upgrade=1 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
missing=()
step() { printf '==> %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

step "uv"
if have uv; then
  [ "$check" -eq 1 ] || uv self update || echo "uv self update skipped (uv was not installed by the standalone installer)"
elif [ "$check" -eq 1 ]; then
  missing+=("uv")
else
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

step "C++ compiler"
if have c++; then
  c++ --version | sed -n 1p
elif [ "$check" -eq 1 ]; then
  missing+=("C++ compiler")
elif [ "$(uname)" = "Darwin" ]; then
  xcode-select --install || true
  echo "Finish the Xcode command-line tools install, then rerun." >&2
  exit 1
elif have apt-get; then
  sudo apt-get update && sudo apt-get install -y build-essential
elif have dnf; then
  sudo dnf install -y gcc-c++ make
else
  echo "Install a C++20 compiler (GCC 11+ or Clang 15+), then rerun." >&2
  exit 1
fi

step "Python"
if [ "$check" -eq 1 ]; then
  [ -d .venv ] || missing+=(".venv")
else
  uv python install
  [ -d .venv ] || uv venv --seed .venv
fi

if [ "$check" -eq 0 ]; then
  step "pios-algo (compiles the C++ module)"
  if [ "$upgrade" -eq 1 ]; then
    uv pip install --python .venv/bin/python --upgrade -e ".[dev]"
  else
    uv pip install --python .venv/bin/python -e ".[dev]"
  fi
fi

step "C++ module"
if [ -x .venv/bin/python ] && .venv/bin/python -c \
  "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pios_algo_compute') else 1)"; then
  echo "pios_algo_compute is built"
else
  missing+=("C++ module not built")
fi

if [ "${#missing[@]}" -gt 0 ]; then
  echo "Missing: ${missing[*]}. Run: bash scripts/bootstrap.sh" >&2
  exit 1
fi
echo "Ready. Activate with: source .venv/bin/activate"
