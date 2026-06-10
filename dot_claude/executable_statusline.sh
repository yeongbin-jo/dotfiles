#!/usr/bin/env bash
# ~/.claude/statusline.sh — Claude Code status line (chezmoi 관리)
# stdin = 세션 JSON
#   좌: 모델 · 디렉터리 · git 브랜치
#   우(터미널 오른쪽 끝 정렬): 🗓️ Nd HH:mm:ss 주간 리셋 카운트다운 + 잔여량 프로그레스 바
#   ※ 카운트다운 실시간 틱하려면 settings.json 에 "refreshInterval": 1 필요
#   ※ 우측 정렬은 Claude Code 가 COLUMNS env 를 주입하는 v2.1.153+ 필요 (미주입 시 좌측 fallback)
python3 -c '
import sys, json, os, re, subprocess, time

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

c = lambda code, s: "\x1b[%sm%s\x1b[0m" % (code, s)
left = [c("38;5;75", model), c("38;5;252", base)]
if branch:
    left.append(c("38;5;114", "⎇ " + branch))
left_s = "  ".join(left)

def fmt_countdown(secs):   # Nd HH:mm:ss (하루 미만이면 HH:mm:ss)
    if secs <= 0:
        return "now"
    dd, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return "%dd %02d:%02d:%02d" % (dd, h, m, s) if dd else "%02d:%02d:%02d" % (h, m, s)

def bar(remaining, width=14):   # 잔여율 게이지 — 퍼센트 텍스트를 바 안에 오버레이
    txt = ("%d%%" % remaining).center(width)
    filled = max(0, min(width, round(width * remaining / 100)))
    col = "114" if remaining > 50 else "178" if remaining > 20 else "167"
    return ("\x1b[48;5;%s;38;5;235;1m%s\x1b[0m" % (col, txt[:filled]) +
            "\x1b[48;5;237;38;5;250m%s\x1b[0m" % txt[filled:])

right_s = ""
sd = (d.get("rate_limits") or {}).get("seven_day") or {}
up = sd.get("used_percentage")
if up is not None:
    remaining = max(0, min(100, 100 - round(up)))
    ra = sd.get("resets_at")
    timer = "\U0001F5D3\uFE0F " + (fmt_countdown(int(ra - time.time())) if ra else "?")
    right_s = c("38;5;250", timer) + "  " + bar(remaining)

if not right_s:
    print(left_s)
else:
    ansi = re.compile("\x1b\\[[0-9;]*m")
    def vis(s):   # 표시 폭: ANSI 제거, 이모지=2칸, VS16=0칸
        s = ansi.sub("", s)
        return sum(0 if ch == "\uFE0F" else 2 if ord(ch) >= 0x1F300 else 1 for ch in s)
    try:
        cols = int(os.environ.get("COLUMNS") or 0)
    except ValueError:
        cols = 0
    pad = cols - vis(left_s) - vis(right_s) - 1 if cols else 0
    print(left_s + " " * max(2, pad) + right_s)
'
