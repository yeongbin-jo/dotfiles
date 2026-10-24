#!/usr/bin/env bash
set -euo pipefail

# python 은 PATH 의 python3(pyenv shim)을 거치지 않고 절대경로로 부른다.
# shim 한 번이 bash 스크립트 ~10개를 연쇄 실행하는데, 이 래퍼는 세션마다 매초 돈다
# (refreshInterval 1). 그 프로세스 폭주가 macOS 26 커널 zone data.kalloc.1024 누수를
# 키워 약 4일마다 panic 을 냈다 — shim 경유 1회 ~20개, 직접 실행 ~0개 (2026-10-05 측정).
# statusline.sh 와 그 안의 loop-status.py 도 이 값을 물려받는다.
if [ -z "${STATUSLINE_PYTHON:-}" ]; then
  for STATUSLINE_PYTHON in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    [ -x "$STATUSLINE_PYTHON" ] && break
  done
fi
export STATUSLINE_PYTHON
export STATUSLINE_OWNER_PID="$PPID"

tmp="$(mktemp "${TMPDIR:-/tmp}/claude-statusline.XXXXXX")"
cleanup() {
  rm -f "$tmp"
}
trap cleanup EXIT

cat > "$tmp"

if [ -x "$HOME/.claude/tmux-status-cache.py" ]; then
  "$STATUSLINE_PYTHON" "$HOME/.claude/tmux-status-cache.py" < "$tmp" >/dev/null 2>&1 || true
fi

if [ -x "$HOME/.claude/statusline.sh" ]; then
  "$HOME/.claude/statusline.sh" < "$tmp"
fi
