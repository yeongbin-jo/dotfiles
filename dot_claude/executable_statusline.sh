#!/usr/bin/env bash
# ~/.claude/statusline.sh - Claude Code session label.
# Resource telemetry is rendered by tmux; this line only identifies the session.
python3 -c '
import json
import os
import subprocess
import sys

try:
    d = json.load(sys.stdin)
except Exception:
    d = {}

model = (d.get("model") or {}).get("display_name") or "?"
cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or os.getcwd()
base = os.path.basename(cwd.rstrip("/")) or cwd

branch = ""
try:
    branch = subprocess.run(
        ["git", "-C", cwd, "branch", "--show-current"],
        capture_output=True,
        text=True,
        timeout=1,
    ).stdout.strip()
except Exception:
    pass

def c(code, s):
    return "\x1b[%sm%s\x1b[0m" % (code, s)

parts = [c("38;5;75", model), c("38;5;252", base)]
if branch:
    parts.append(c("38;5;114", "⎇ " + branch))

print("  ".join(parts))
'
