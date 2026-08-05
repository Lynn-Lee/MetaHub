#!/usr/bin/env bash
set -euo pipefail

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="${PYTHON:-python}"
fi

if "$PYTHON_BIN" -m pytest --collect-only -q -m gate --strict-markers | grep -q '^tests/'; then
  "$PYTHON_BIN" -m pytest -v -m gate --strict-markers
else
  echo "No gate tests collected yet; gate suite starts with T2.4/T8.3."
fi
