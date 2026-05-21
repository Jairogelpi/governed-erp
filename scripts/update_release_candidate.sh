#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/erpguard/app}"
PYTHON_BIN="${PYTHON_BIN:-/opt/erpguard/.venv/bin/python}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SERVICE_NAME="${SERVICE_NAME:-erpguard}"

cd "${APP_DIR}"
git pull origin main
"${PYTHON_BIN}" -m pip install -e ".[dev]"

if command -v systemctl >/dev/null 2>&1; then
  # Default service command: sudo systemctl restart erpguard
  sudo systemctl restart "${SERVICE_NAME}"
  sudo systemctl status "${SERVICE_NAME}" --no-pager
else
  echo "systemctl not found; restart ${SERVICE_NAME} manually before running ops_check."
fi

"${PYTHON_BIN}" scripts/ops_check.py --base-url "${BASE_URL}"
