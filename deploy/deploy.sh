#!/usr/bin/env bash
# Run on the host box (192.168.1.202), from /opt/rnk/the-gift (or wherever the
# library lives), to redeploy after a git pull or rsync. One stdlib process
# serves the landing page, the listings, and the files — no build step.
set -euo pipefail

if systemctl is-active --quiet the-gift; then
  sudo systemctl restart the-gift
else
  sudo systemctl enable --now the-gift
fi

sleep 1
curl -sf http://127.0.0.1:8770/ | grep -q "<h1>The Gift</h1>" && echo "the-gift: landing page OK"
