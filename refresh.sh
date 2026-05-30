#!/bin/bash
# image2prompt refresh — pull upstream cases, rebuild, deploy.
# Safe to run on a cron. Logs to ~/projects/image2prompt/.refresh.log
set -euo pipefail

cd "$(dirname "$0")"
LOG=".refresh.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') refresh starting ==="
  python3 build.py
  echo "--- deploying to vercel ---"
  /Users/carlfung/.nvm/versions/node/v22.18.0/bin/vercel deploy --prod --yes
  echo "=== done ==="
  echo
} >> "$LOG" 2>&1

# Tail the last few lines so a manual `bash refresh.sh` shows the result
tail -20 "$LOG"
