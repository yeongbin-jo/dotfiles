#!/usr/bin/env python3
from __future__ import annotations

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

now = int(time.time())
resets_at = seven_day.get("resets_at")
fingerprint = [
    context_used,
    context.get("total_input_tokens"),
    context.get("total_output_tokens"),
    (data.get("cost") or {}).get("total_cost_usd"),
    weekly_remaining,
    resets_at,
]

root = cache_dir()
slug = home_slug()
latest_path = root / f"latest-{slug}.json"
try:
    existing_latest = json.loads(latest_path.read_text())
except Exception:
    existing_latest = {}

session = data.get("session_id")
owner = claude_owner() if session else None
session_path = None
existing_session = {}
if session and owner:
    key = hashlib.sha256((str(config_dir()) + "\0" + session).encode()).hexdigest()[:20]
    session_path = root / f"session-{key}.json"
    try:
        loaded = json.loads(session_path.read_text())
        if loaded.get("owner_pid") == owner[0] and loaded.get("owner_started") == owner[1]:
            existing_session = loaded
    except Exception:
        existing_session = {}

# refreshInterval=1 calls this script every second on an idle pane with the exact
# same stdin JSON. Only stamp a new timestamp when the session's payload changed.
updated_at = now
if existing_session and existing_session.get("fingerprint") == fingerprint:
    updated_at = int(existing_session.get("updated_at") or now)
elif not session and existing_latest.get("fingerprint") == fingerprint:
    updated_at = int(existing_latest.get("updated_at") or now)

state = {
    "cwd": cwd,
    "context_used_percent": context_used,
    "weekly_remaining_percent": weekly_remaining,
    "weekly_resets_at": resets_at,
    "updated_at": updated_at,
    "fingerprint": fingerprint,
}

# Account quota remains compatible with the dashboard's existing reader.
# Reconcile across panes of the same account: within one reset window remaining
# quota only decreases, so an idle pane re-rendering an old turn must not
# overwrite a lower remaining percentage.
l_rem = existing_latest.get("weekly_remaining_percent")
l_res = existing_latest.get("weekly_resets_at")
l_upd = int(existing_latest.get("updated_at") or 0)
if weekly_remaining is not None:
    if (l_res == resets_at and isinstance(l_rem, (int, float))
            and not isinstance(l_rem, bool)):
        if weekly_remaining > l_rem:
            state["weekly_remaining_percent"] = int(l_rem)
            state["updated_at"] = max(updated_at, l_upd)
            if existing_latest.get("source"):
                state["source"] = existing_latest["source"]
        elif weekly_remaining == l_rem and l_upd >= updated_at:
            state["updated_at"] = l_upd
            if existing_latest.get("source"):
                state["source"] = existing_latest["source"]
    atomic_write(latest_path, state)
elif l_rem is not None and l_res is not None:
    state["weekly_remaining_percent"] = int(l_rem)
    state["weekly_resets_at"] = l_res
    state["updated_at"] = l_upd or updated_at

if session and owner and session_path is not None:
    state.update(session_id=session, owner_pid=owner[0], owner_started=owner[1])
    atomic_write(session_path, state)
    atomic_write(root / f"owner-{slug}-{owner[0]}.json",
                 {"session_id": session, "owner_started": owner[1]})

print("")
