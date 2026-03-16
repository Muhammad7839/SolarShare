#!/usr/bin/env bash
# Unified command runner that operationalizes Codex skills for this repository.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="python3"

if [[ -x "$BACKEND_DIR/.venv/bin/python3" ]]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python3"
elif [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
fi

print_usage() {
  cat <<'EOF'
Usage:
  ./scripts/skill-suite.sh audit
  ./scripts/skill-suite.sh bug-hunt
  ./scripts/skill-suite.sh fullstack
  ./scripts/skill-suite.sh pdf /absolute/or/relative/path/to/file.pdf
  ./scripts/skill-suite.sh fitgpt-check
  ./scripts/skill-suite.sh skills-help
EOF
}

run_audit() {
  echo "[codebase-auditor] Running repository health checks..."
  (
    cd "$BACKEND_DIR"
    "$PYTHON_BIN" -m pytest -q
  )
  node --check "$ROOT_DIR/backend/app/static/app.js"
  node --check "$ROOT_DIR/backend/app/static/site.js"
  echo "[codebase-auditor] Completed."
}

run_bug_hunt() {
  echo "[bug-hunter] Running targeted regression suite..."
  (
    cd "$BACKEND_DIR"
    "$PYTHON_BIN" -m pytest -q -k "validation or live_comparison or contact_inquiry or rate_limit"
  )
  echo "[bug-hunter] Running API edge-case smoke checks..."
  (
    cd "$BACKEND_DIR"
    "$PYTHON_BIN" - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

health = client.get("/health")
assert health.status_code == 200
assert health.headers.get("x-request-id")

bad_live = client.post(
    "/live-comparison",
    json={"location": "", "monthly_usage_kwh": -10, "priority": "invalid"},
)
assert bad_live.status_code == 422

bad_contact = client.post(
    "/contact-inquiries",
    json={"name": "A", "email": "bad-email", "interest": "other", "message": "short"},
)
assert bad_contact.status_code == 422

print("edge-case smoke checks passed")
PY
  )
  echo "[bug-hunter] Completed."
}

run_pdf() {
  local pdf_path="${1:-}"
  if [[ -z "$pdf_path" ]]; then
    echo "Missing PDF path."
    print_usage
    exit 1
  fi
  "$PYTHON_BIN" "$ROOT_DIR/scripts/pdf_extract_summary.py" "$pdf_path"
}

run_fitgpt_check() {
  echo "[fitgpt-stack-engineer] Checking for Android stack readiness..."
  if [[ -d "$ROOT_DIR/android" || -d "$ROOT_DIR/app/src/main" ]]; then
    echo "Android artifacts detected. FastAPI + Android cross-layer work can be applied directly."
  else
    echo "No Android client found in this repo yet."
    echo "Current integration applies FastAPI + web layers only."
  fi
}

run_skills_help() {
  echo "[skill-creator] Use when creating/updating custom skills in ~/.codex/skills."
  echo "[skill-installer] Use when listing/installing skills from openai/skills or GitHub."
  echo "Project-facing commands are provided via: audit, bug-hunt, fullstack, pdf, fitgpt-check."
}

if [[ $# -lt 1 ]]; then
  print_usage
  exit 1
fi

command="$1"
shift || true

case "$command" in
  audit)
    run_audit
    ;;
  bug-hunt)
    run_bug_hunt
    ;;
  fullstack)
    echo "[senior-fullstack-engineer] Running full workflow..."
    run_audit
    run_bug_hunt
    run_fitgpt_check
    echo "[senior-fullstack-engineer] Completed."
    ;;
  pdf)
    run_pdf "${1:-}"
    ;;
  fitgpt-check)
    run_fitgpt_check
    ;;
  skills-help)
    run_skills_help
    ;;
  *)
    echo "Unknown command: $command"
    print_usage
    exit 1
    ;;
esac
