#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
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


def write_cache(cwd: str, state: dict) -> None:
    path = cache_dir() / f"{cache_key(cwd)}.json"
    latest = cache_dir() / "latest.json"
    payload = json.dumps(state, separators=(",", ":"))
    for target in (path, latest):
        tmp = target.with_suffix(".tmp")
        tmp.write_text(payload)
        os.replace(tmp, target)


def ansi(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m"


def context_bar_color(used: int) -> str:
    if used < 40:
        return "153"
    if used < 65:
        return "111"
    if used < 82:
        return "131"
    return "210"


def weekly_bar_color(remaining: int) -> str:
    if remaining > 50:
        return "114"
    if remaining > 30:
        return "178"
    if remaining > 12:
        return "208"
    return "167"


def bar(value: int, color: str, width: int = 14) -> str:
    value = max(0, min(100, int(round(value))))
    text = f"{value}% ".rjust(width)
    filled = max(0, min(width, round(width * value / 100)))
    return (
        "\x1b[38;5;245m[\x1b[0m"
        + f"\x1b[48;5;{color};38;5;235;1m{text[:filled]}\x1b[0m"
        + f"\x1b[48;5;237;38;5;250m{text[filled:]}\x1b[0m"
        + "\x1b[38;5;245m]\x1b[0m"
    )


def countdown_text(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{secs:02}"
    return f"{hours:02}:{minutes:02}:{secs:02}"


def current_branch(cwd: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        ).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    model = (data.get("model") or {}).get("display_name") or "Claude"
    branch = current_branch(cwd)

    context = data.get("context_window") or {}
    used_context = clamp_percent(
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
        "model": model,
        "branch": branch,
        "context_used_percent": used_context,
        "weekly_remaining_percent": weekly_remaining,
        "weekly_resets_at": seven_day.get("resets_at"),
        "updated_at": int(time.time()),
    }
    write_cache(cwd, state)

    left = [
        ansi("38;5;221;1", " CLAUDE "),
        ansi("38;5;252", os.path.basename(cwd.rstrip("/")) or cwd),
    ]
    if branch:
        left.append(ansi("38;5;114", "⎇ " + branch))
    left.append(ansi("38;5;250", "CONTEXT ") + bar(used_context, context_bar_color(used_context)))

    right = ""
    if weekly_remaining is not None:
        reset = seven_day.get("resets_at")
        timer = countdown_text(int(reset - time.time())) if isinstance(reset, (int, float)) else "?"
        right = (
            ansi("38;5;250", "WEEKLY RESET ")
            + ansi("38;5;221", "🗓️ " + timer)
            + " "
            + bar(weekly_remaining, weekly_bar_color(weekly_remaining))
        )

    if not right:
        print("  ".join(left))
    else:
        print("  ".join(left) + "  " + right)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
