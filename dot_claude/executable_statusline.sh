#!/usr/bin/env bash
# ~/.claude/statusline.sh — Claude Code status line (chezmoi 관리)
# stdin = 세션 JSON → 모델 · 디렉터리 · git 브랜치 · 사용량
#   5h: used% + 리셋까지 h:mm:ss (초단위) / 7d: used% + Dd h:mm (분단위)
#   ※ 카운트다운 실시간 틱하려면 settings.json 에 "refreshInterval": 1 필요
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

def fmt_hms(secs):   # 5h: 초단위
    if secs <= 0:
        return "now"
    h, r = divmod(secs, 3600); m, s = divmod(r, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)

def fmt_dhm(secs):   # 7d: 분단위
    if secs <= 0:
        return "now"
    dd, r = divmod(secs, 86400); h, r = divmod(r, 3600); m = r // 60
    return "%dd %d:%02d" % (dd, h, m) if dd else "%d:%02d" % (h, m)

def seg(label, info, fmt):
    info = info or {}
    up = info.get("used_percentage")
    if up is None:
        return None
    ra = info.get("resets_at")
    cd = " ↻" + fmt(int(ra - time.time())) if ra else ""
    return "%s %d%%%s" % (label, round(up), cd)

rl = d.get("rate_limits") or {}
c = lambda code, s: "\x1b[%sm%s\x1b[0m" % (code, s)
parts = [c("38;5;75", model), c("38;5;252", base)]
if branch:
    parts.append(c("38;5;114", "⎇ " + branch))
segs = [s for s in (seg("5h", rl.get("five_hour"), fmt_hms),
                    seg("7d", rl.get("seven_day"), fmt_dhm)) if s]
if segs:
    parts.append(c("38;5;208", "│ " + "  ".join(segs)))
print("  ".join(parts))
'
