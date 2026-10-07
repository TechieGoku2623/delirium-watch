#!/usr/bin/env bash
# cast -> gif / svg / mp4 via agg and ffmpeg. Captions burn in from shots.yaml.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${ROOT}/.venv/bin:${HOME}/.local/bin:${PATH}"
export TERM=xterm-256color
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
uv run --with pyyaml --with pillow python demo/lib/render_all.py
