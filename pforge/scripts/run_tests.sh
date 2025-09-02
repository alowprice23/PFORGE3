#!/usr/bin/env bash
# Run backend PyTests + frontend Jest tests

set -euo pipefail

echo "🔬  Python unit tests…"
pytest -q tests/

echo "🧪  Frontend Jest tests…"
# Add frontend tests here when available

echo "✅  All tests passing"
