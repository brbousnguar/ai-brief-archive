#!/bin/bash
# Build the venv narrate.py runs in. It lives outside the repo on purpose: the
# publish hook commits with `git add -A`, so a venv in the checkout would be pushed.
#
#   tts/setup.sh            # create or update
#   tts/setup.sh --fresh    # rebuild from scratch
#
# The Kokoro model (~330 MB) downloads to the Hugging Face cache on first use.

set -euo pipefail

VENV="${AIBRIEF_TTS_VENV:-$HOME/.local/share/ai-brief-tts/venv}"
PY="${PYTHON:-/opt/homebrew/bin/python3.12}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--fresh" ] && [ -d "$VENV" ]; then
    rm -rf "${VENV:?}"
fi
if [ ! -x "$VENV/bin/python" ]; then
    mkdir -p "$(dirname "$VENV")"
    "$PY" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r "$HERE/requirements.txt"
"$VENV/bin/python" -c "import mlx_audio, misaki, en_core_web_sm; print('ready:', '$VENV')"
