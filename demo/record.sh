#!/usr/bin/env bash
# Regenerates every cast from demo/script/shots.yaml.
# Terminal geometry, prompt, locale, and environment are pinned here so
# every recording matches.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p demo/cast demo/script/captions demo/.tmp/home

export PATH="${ROOT}/.venv/bin:${HOME}/.local/bin:${PATH}"
export TERM=xterm-256color
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export COLUMNS=100
export LINES=30
export PS1='$ '
unset NO_COLOR
# Drop credential-bearing variables so a leaked env cannot appear in a frame.
while IFS= read -r name; do
  unset "${name}" || true
done < <(env | awk -F= '
  toupper($1) ~ /(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AWS_|OPENAI|ANTHROPIC|GEMINI)/ { print $1 }
')

uv run --with pyyaml python demo/lib/record_all.py
