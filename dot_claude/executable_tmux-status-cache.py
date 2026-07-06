#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def cache_dir() -> Path:
    root = os.environ.get("TMPDIR") or "/tmp"
    path = Path(root) / "claude-tmux-statusline"
    path.mkdir(parents=True, exist_ok=True)
    return path


def clamp_percent(value) -> int:
    try:
        return int(round(min(100.0, max(0.0, float(value)))))
    except Exception:
        return 0


def cache_key(cwd: str) -> str:
    return hashlib.sha256(cwd.encode("utf-8")).hexdigest()[:16]


try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
context = data.get("context_window") or {}
# 갓 연 세션은 used_percentage / remaining_percentage 가 모두 null(키는 존재)로 들어온다.
# dict.get(key, default) 는 "키 부재"일 때만 default 를 주고, "키 있으나 값 null"이면 None 을
# 그대로 돌려준다 → 예전엔 clamp_percent(None)=0, 100-0=100 이 되어 빈 컨텍스트가 100%로 표시됐다.
used_value = context.get("used_percentage")
if used_value is None:
    remaining_value = context.get("remaining_percentage")
    used_value = 100 - clamp_percent(remaining_value) if remaining_value is not None else 0
context_used = clamp_percent(used_value)

seven_day = (data.get("rate_limits") or {}).get("seven_day") or {}
weekly_used = seven_day.get("used_percentage")
weekly_remaining = None
if weekly_used is not None:
    weekly_remaining = max(0, min(100, 100 - clamp_percent(weekly_used)))

state = {
    "cwd": cwd,
    "context_used_percent": context_used,
    "weekly_remaining_percent": weekly_remaining,
    "weekly_resets_at": seven_day.get("resets_at"),
    "updated_at": int(time.time()),
}

payload = json.dumps(state, separators=(",", ":"))
for path in (cache_dir() / f"{cache_key(cwd)}.json", cache_dir() / "latest.json"):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(payload)
    os.replace(tmp, path)

# The wrapper discards this output and then renders the normal Claude statusline.
print("")
