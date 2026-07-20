#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

export ICEBERG_CONFIG="${ICEBERG_CONFIG:-config.demo.json}"

echo "===================================================="
echo "  Iceberg Live Demo"
echo "===================================================="
echo "Using config: $ICEBERG_CONFIG"
echo "Open: http://127.0.0.1:8765/"
echo
python3 livka_dashboard_refactor_codex.py
python3 live_dashboard_server.py
