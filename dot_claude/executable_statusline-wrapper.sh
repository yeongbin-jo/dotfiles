#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp "${TMPDIR:-/tmp}/claude-statusline.XXXXXX")"
cleanup() {
  rm -f "$tmp"
}
trap cleanup EXIT

cat > "$tmp"

if [ -x "$HOME/.claude/tmux-status-cache.py" ]; then
  "$HOME/.claude/tmux-status-cache.py" < "$tmp" >/dev/null 2>&1 || true
fi

if [ -x "$HOME/.claude/statusline.sh" ]; then
  "$HOME/.claude/statusline.sh" < "$tmp"
fi
