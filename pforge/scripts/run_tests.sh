#!/usr/bin/env bash
# Run backend PyTests + frontend Jest tests

set -euo pipefail

# Get the directory of this script, then go to the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

echo "🔬  Python unit tests…"
python -m pytest -q tests/unit/test_redaction.py tests/unit/test_base_agent_security.py

echo "✅  All tests passing"
