#!/bin/bash
# Publish the AI brief archive when Victor writes a new brief.
#
# Triggered by launchd WatchPaths on Victor's briefs directory. Victor only ever
# writes markdown; this script is the only thing that renders, commits and
# pushes. That split is deliberate — the agent can get the *content* wrong, but
# it cannot half-publish, push garbage, or report a publish that never happened.
#
# Safe to run at any time by hand:  ./publish-hook.sh

set -uo pipefail

REPO="$HOME/Server/sites/ai-brief-archive"
SOURCE="$HOME/Server/agents/openclaw/victor/briefs"
LOG="$HOME/Server/logs/ai-brief-publish.log"

mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "--- $(date '+%Y-%m-%d %H:%M:%S') trigger"

cd "$REPO" || { echo "FATAL: no repo at $REPO"; exit 1; }

# WatchPaths fires the moment a file is touched, which can be mid-heredoc.
# Let the write settle before reading it.
sleep 3

# Parse first and bail quietly on a half-written or malformed file. launchd will
# fire again on the next write, so exiting 0 here avoids retry thrash while
# still refusing to publish something broken.
if ! ./publish.py --source "$SOURCE" --check; then
    echo "SKIP: briefs did not parse (likely a partial write); waiting for next trigger"
    exit 0
fi

./publish.py --source "$SOURCE" || { echo "FATAL: render failed"; exit 1; }

if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    echo "no change to publish"
    exit 0
fi

LATEST=$(ls -1 "$SOURCE"/*.md 2>/dev/null | tail -1 | xargs -I{} basename {} .md)
git add -A
git -c user.name=brbousnguar -c user.email=brbousnguar@gmail.com \
    commit -q -m "content: publish brief ${LATEST:-update}" || {
        echo "nothing staged after all"; exit 0; }

if git push -q origin main; then
    echo "published ${LATEST:-update} -> https://brbousnguar.github.io/ai-brief-archive/"
else
    echo "ERROR: push failed — commit is local only, run 'git push' in $REPO"
    exit 1
fi
