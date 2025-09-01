#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Spin up full pForge stack via docker‑compose and seed demo data
# ────────────────────────────────────────────────────────────────────

set -euo pipefail
COMPOSE_FILE="docker-compose.yml"

echo "🛠  Building & starting containers…"
docker compose -f "$COMPOSE_FILE" up -d --build

echo "⏳  Waiting for core services (redis, neo4j)…"
until docker compose exec neo4j cypher-shell -u neo4j -p neo4jpass "RETURN 1;" >/dev/null 2>&1; do
  sleep 2 && printf '.'
done
echo " ✅"

# Seed sample repo into sandbox (optional)
SAMPLE="data/sample_repos/tiny_todo_app.zip"
if [ -f "$SAMPLE" ]; then
  echo "📦  Seeding sample repo…"
  unzip -qo "$SAMPLE" -d /tmp/tiny_todo_app
  docker compose exec orchestrator python - <<'PY'
from sandbox.fs_manager import copy_into_sandbox
copy_into_sandbox("/tmp/tiny_todo_app")
PY
fi

echo "🚀  pForge is up!  UI →  http://localhost:8080"
