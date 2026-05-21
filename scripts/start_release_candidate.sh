#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
export ERPGUARD_DATABASE_URL="${ERPGUARD_DATABASE_URL:-sqlite:///./erpguard_release_candidate.db}"
export ALLOW_GENERIC_REAL_ODOO_WRITES="${ALLOW_GENERIC_REAL_ODOO_WRITES:-false}"
export ALLOW_R3_R4_REAL_WRITES="${ALLOW_R3_R4_REAL_WRITES:-false}"

python - <<'PY'
from erpguard.db.session import init_db

init_db()
print("Database initialized for ERPGuard release candidate.")
PY

echo "Starting ERPGuard v0.12.0-rc1 on ${HOST}:${PORT}"
echo "Health: http://127.0.0.1:${PORT}/v1/release/health"
exec uvicorn apps.api.main:app --host "${HOST}" --port "${PORT}"
