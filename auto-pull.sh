#!/bin/bash
# Auto-deploy: pull the latest from GitHub every run; if server.py changed,
# syntax-check and restart it. Installed as a 1-minute cron on the VPS so that
# every `git push` goes live on its own — no manual SSH pull needed.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

cd /root/knowledge/life-os || exit 0

BEFORE=$(git rev-parse HEAD 2>/dev/null)
git pull origin main >/dev/null 2>&1
AFTER=$(git rev-parse HEAD 2>/dev/null)

# Nothing new — done.
[ "$BEFORE" = "$AFTER" ] && exit 0

# If the Python backend changed, verify it compiles, then restart on port 8090.
if git diff --name-only "$BEFORE" "$AFTER" 2>/dev/null | grep -q '^server.py$'; then
  if python3 -m py_compile server.py 2>/dev/null; then
    fuser -k 8090/tcp 2>/dev/null
    sleep 1
    nohup python3 server.py > server.log 2>&1 &
  fi
fi

exit 0
