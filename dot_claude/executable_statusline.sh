#!/usr/bin/env bash
# ~/.claude/statusline.sh — Claude Code status line (chezmoi 관리)
# stdin = 세션 JSON
#   좌: 모델 · 디렉터리 · git 브랜치 · 컨텍스트 사용량 게이지(사용↑ 하늘→파랑→검붉→빨강)
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

def ctx_seg(used, width=14):   # 컨텍스트 사용량 바 — 우측 잔여량 바와 동일 디자인, 색만 사용량 그라데이션(사용↑: 하늘117→파랑33→검붉124→빨강196)
    used = max(0, min(100, round(used)))
    txt = ("%d%% " % used).rjust(width)
    filled = max(0, min(width, round(width * used / 100)))
    col = "153" if used < 40 else "111" if used < 65 else "131" if used < 82 else "210"   # 파스텔: 연하늘→연파랑→더스티레드→살몬
    return ("\x1b[38;5;245m[\x1b[0m" +
            "\x1b[48;5;%s;38;5;235;1m%s\x1b[0m" % (col, txt[:filled]) +
            "\x1b[48;5;237;38;5;250m%s\x1b[0m" % txt[filled:] +
            "\x1b[38;5;245m]\x1b[0m")

left = [c("38;5;75", model), c("38;5;252", base)]
if branch:
    left.append(c("38;5;114", "⎇ " + branch))
# 자율 루프 표시 — ~/.claude/loop-state/<session_id>.json 이 가리키는 컨트롤 노트에서 읽는다.
# 세션 단위로 스코프한다: 전역 파일이던 첫 판은 이 머신의 모든 세션에 남의 루프를 그렸다.
# 상태 파일이 없으면 아무것도 출력하지 않으므로 루프를 돌리지 않는 세션은 그대로.
try:
    _loop = subprocess.run([os.path.expanduser("~/.claude/loop-status.py"),
                            d.get("session_id") or ""],
                           capture_output=True, text=True, timeout=1).stdout.strip()
    if _loop:
        left.append(_loop)
except Exception:
    pass
cw = d.get("context_window") or {}
cu = cw.get("used_percentage")
if cu is not None:
    left.append(ctx_seg(cu))
left_s = "  ".join(left)

def fmt_countdown(secs):   # Nd HH:mm:ss (하루 미만이면 HH:mm:ss)
    if secs <= 0:
        return "now"
    dd, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return "%dd %02d:%02d:%02d" % (dd, h, m, s) if dd else "%02d:%02d:%02d" % (h, m, s)

def bar(remaining, width=14):   # 잔여율 게이지 — 퍼센트 텍스트를 바 안 우측 정렬로 오버레이
    txt = ("%d%% " % remaining).rjust(width)
    filled = max(0, min(width, round(width * remaining / 100)))
    col = "114" if remaining > 50 else "178" if remaining > 20 else "167"
    return ("\x1b[38;5;245m[\x1b[0m" +
            "\x1b[48;5;%s;38;5;235;1m%s\x1b[0m" % (col, txt[:filled]) +
            "\x1b[48;5;237;38;5;250m%s\x1b[0m" % txt[filled:] +
            "\x1b[38;5;245m]\x1b[0m")

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
    # CC UI 가 statusline 좌우에 자체 패딩을 둠 → COLUMNS 그대로 쓰면 … 잘림.
    # ccstatusline 과 동일하게 6칸 예약 (full-width flex 모드의 검증된 마진)
    pad = cols - vis(left_s) - vis(right_s) - 6 if cols else 0
    print(left_s + " " * max(2, pad) + right_s)
'
