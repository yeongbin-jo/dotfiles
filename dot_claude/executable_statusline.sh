#!/usr/bin/env bash
# ~/.claude/statusline.sh — Claude Code status line (chezmoi 관리)
# Claude 가 세션 JSON 을 stdin 으로 넘김
#   → 모델 · 디렉터리 · git 브랜치 · 사용량(5h/7d used% + 리셋까지, Pro·Max 한정)
python3 -c '
import sys, json, os, subprocess, time
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
model = (d.get("model") or {}).get("display_name") or "?"
cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or os.getcwd()
base = os.path.basename(cwd.rstrip("/")) or cwd
branch = ""
try:
    branch = subprocess.run(["git", "-C", cwd, "branch", "--show-current"],
                            capture_output=True, text=True, timeout=1).stdout.strip()
except Exception:
    pass

def reset_str(ra):
    if not ra:
        return ""
    delta = ra - time.time()
    if delta <= 0:
        return "↻now"
    if delta < 3600:
        return "↻%dm" % round(delta / 60)
    if delta < 86400:
        return "↻%dh" % round(delta / 3600)
    return "↻%dd" % round(delta / 86400)

def seg(label, info):
    info = info or {}
    up = info.get("used_percentage")
    if up is None:
        return None
    rs = reset_str(info.get("resets_at"))
    return "%s %d%%%s" % (label, round(up), (" " + rs if rs else ""))

rl = d.get("rate_limits") or {}
c = lambda code, s: "\x1b[%sm%s\x1b[0m" % (code, s)
parts = [c("38;5;75", model), c("38;5;252", base)]
if branch:
    parts.append(c("38;5;114", "⎇ " + branch))
segs = [s for s in (seg("5h", rl.get("five_hour")), seg("7d", rl.get("seven_day"))) if s]
if segs:
    parts.append(c("38;5;208", "│ " + "  ".join(segs)))
print("  ".join(parts))
'
