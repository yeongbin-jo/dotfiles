#!/usr/bin/env python3
import hashlib
import json
import math
import os
import subprocess
import tempfile
import sys
import time
from pathlib import Path


def cache_dir() -> Path:
    root = os.environ.get("TMPDIR") or "/tmp"
    path = Path(root) / "claude-tmux-statusline"
    path.mkdir(parents=True, exist_ok=True)
    return path


def clamp_percent(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return round(value)


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")).resolve()


def home_slug() -> str:
    return hashlib.sha1(str(config_dir()).encode("utf-8")).hexdigest()[:12]


def atomic_write(path: Path, state: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(state, handle, separators=(",", ":"))
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def claude_owner() -> tuple[int, str] | None:
    pid = int(os.environ.get("STATUSLINE_OWNER_PID") or os.getppid())
    for _ in range(8):
        if pid <= 1:
            break
        try:
            result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "pid=,ppid=,lstart=,comm="],
                                    capture_output=True, text=True, timeout=0.2, check=True,
                                    env=dict(os.environ, LC_ALL="C"))
            fields = result.stdout.split(None, 7)
            command = fields[7].strip()
            if Path(command).name == "claude" or "/claude/versions/" in command:
                return int(fields[0]), " ".join(fields[2:7])
            pid = int(fields[1])
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            break
    return None


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
    remaining_value = clamp_percent(context.get("remaining_percentage"))
    used_value = 100 - remaining_value if remaining_value is not None else None
context_used = clamp_percent(used_value) if used_value is not None else None

seven_day = (data.get("rate_limits") or {}).get("seven_day") or {}
weekly_used = clamp_percent(seven_day.get("used_percentage"))
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

root = cache_dir()
# Account quota remains compatible with the dashboard's existing reader.
if weekly_remaining is not None:
    atomic_write(root / f"latest-{home_slug()}.json", state)
session = data.get("session_id")
owner = claude_owner() if session else None
if session and owner:
    state.update(session_id=session, owner_pid=owner[0], owner_started=owner[1])
    key = hashlib.sha256((str(config_dir()) + "\0" + session).encode()).hexdigest()[:20]
    atomic_write(root / f"session-{key}.json", state)
    atomic_write(root / f"owner-{home_slug()}-{owner[0]}.json",
                 {"session_id": session, "owner_started": owner[1]})

print("")
