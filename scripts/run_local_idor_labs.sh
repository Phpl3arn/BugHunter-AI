#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Projects/Claude-BugHunter
PY="$HOME/bughunter-venv/bin/python"
"$PY" lab/idor_server.py &
VULN_PID=$!
"$PY" lab/idor_safe_server.py &
SAFE_PID=$!
cleanup() { kill "$VULN_PID" "$SAFE_PID" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM
printf 'Local lab started. Ctrl+C stops both services.\n'
wait -n "$VULN_PID" "$SAFE_PID" || true
