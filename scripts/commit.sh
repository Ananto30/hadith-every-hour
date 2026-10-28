#!/bin/bash
set -euo pipefail

git add .

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "Update Hadith number track"

for attempt in 1 2 3 4 5; do
  if git pull --rebase --autostash origin main \
    && git push origin main; then
    exit 0
  fi
  sleep $((attempt * 5))
done

echo "Failed to push changes." >&2
exit 1
