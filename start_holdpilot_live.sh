#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

export HOLDPILOT_CONFIG="${HOLDPILOT_CONFIG:-config.demo.json}"

echo "===================================================="
echo "  HoldPilot Live Demo"
echo "===================================================="
echo "Using config: $HOLDPILOT_CONFIG"
echo "Open: http://127.0.0.1:8765/"
echo
python3 livka_dashboard_refactor_codex.py
python3 live_dashboard_server.py
