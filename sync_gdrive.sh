#!/usr/bin/env bash
set -euo pipefail

REMOTE="gdrive"
REMOTE_PATH="LifeOS-Vault/life-os"
LOCAL_DIR="/root/knowledge/life-os"
COMMIT_MSG="Sync from Google Drive via rclone $(date +"%Y-%m-%d %H:%M:%S")"

cd "$LOCAL_DIR"

# Sync from Drive to local (update only)
rclone copy "$REMOTE:$REMOTE_PATH/" . --update --progress

# Commit & push if any changes
if ! git diff --quiet HEAD; then
    echo "Changes detected – committing…"
    git add -A
    git commit -m "$COMMIT_MSG"
    git push origin main
    echo "Pushed to GitHub"
else
    echo "No changes to commit"
fi
