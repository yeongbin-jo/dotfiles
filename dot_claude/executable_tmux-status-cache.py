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
context_used = clamp_percent(
    context.get("used_percentage")
    if context.get("used_percentage") is not None
    else 100 - clamp_percent(context.get("remaining_percentage", 100))
)

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
