#!/usr/bin/env bash
# MAAI Agent Platform — Update & Restart Script
# Usage: ./update.sh [client-name]
#
# What this script does:
#   1. Stops all running containers
#   2. Pulls latest code from the repo
#   3. Rebuilds and restarts everything via bootstrap.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT="${1:-default}"

# ── Docker command detection ─────────────────────────────────────────────────
if command -v docker.exe &>/dev/null; then
  DOCKER="docker.exe"
elif command -v docker &>/dev/null; then
  DOCKER="docker"
else
  echo "[update] ERROR Docker not found." >&2
  exit 1
fi

echo "============================================"
echo "  MAAI Agent Platform — Update & Restart"
echo "============================================"
echo ""

# ── Step 1: Stop everything ──────────────────────────────────────────────────
echo "[update] Stopping all containers..."
${DOCKER} compose --profile gpu --profile cpu down 2>/dev/null || true
echo "[update] All containers stopped."

# ── Step 2: Pull latest code ─────────────────────────────────────────────────
echo "[update] Pulling latest code from repository..."
git pull --ff-only origin master
echo "[update] Code updated."

# ── Step 3: Rebuild and restart ──────────────────────────────────────────────
echo "[update] Running bootstrap..."
echo ""
bash "${SCRIPT_DIR}/bootstrap.sh" "${CLIENT}"
