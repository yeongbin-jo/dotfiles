#!/usr/bin/env python3
"""nydus tmux 세션의 Claude Code 창을 중단 시점 그대로 되살린다.

배경
----
이 맥에는 tmux-resurrect + continuum 이 깔려 있어(15분 자동저장, 서버 시작 시 자동복원)
강제종료/배터리 방전 뒤에도 **창·cwd·스크롤백은** 돌아온다. 그런데 resurrect 가 되살리는
프로그램은 `@resurrect-processes` 화이트리스트뿐이라 **claude 프로세스는 살아나지 않고
맨 셸만 남는다.** 이 스크립트가 그 빈칸을 메운다.

핵심 문제는 "어느 창이 어느 대화였는가" 다. 죽은 뒤에 추측하면 틀린다(mtime 순서로
고르면 같은 cwd 를 쓰는 창끼리 뒤바뀐다 — 실제로 그렇게 한 번 틀렸다). 그래서 이 스크립트는
**살아있을 때 원장(ledger)을 남겨두고**, 복구는 그 원장을 재생하기만 한다.

세션 ID 해석 순서:
  1. argv 의 `--resume/-r <id>` 또는 `--session-id <id>`  ← 확정
  2. 없으면(맨 `claude` 나 `-c` 로 띄운 경우) 창의 화면 내용을 그 cwd 의 세션 파일들과
     대조해 추론 — 화면에 보이는 문장이 가장 많이 들어있는 파일을 고른다.

사용법:
  nydus_sessions.py snapshot          # 원장 기록 (살아있을 때, 주기적으로)
  nydus_sessions.py status            # 원장 vs 현재 상태 비교 (죽은 창 표시)
  nydus_sessions.py restore [--dry-run] [--window N]
  nydus_sessions.py install-hook      # continuum 저장 때마다 snapshot 되도록 배선
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATE_DIR = Path.home() / ".local/state/nydus-revive"
# NYDUS_LEDGER 로 원장 경로를 갈아끼울 수 있다 (테스트/격리용).
LEDGER = Path(os.environ.get("NYDUS_LEDGER") or (STATE_DIR / "ledger.json"))
HISTORY = STATE_DIR / "history"
HISTORY_KEEP = 20
PROJECTS = Path.home() / ".claude/projects"

# argv 에서 세션을 고르는 플래그 — 복구 커맨드를 만들 때 전부 걷어내고 --resume 로 통일한다.
SESSION_FLAGS_WITH_VALUE = {"--resume", "-r", "--session-id"}
SESSION_FLAGS_BARE = {"--continue", "-c", "--fork-session"}

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
BOXY = re.compile(r"^[\s─━│┃┌┐└┘├┤┬┴┼╭╮╯╰═║╔╗╚╝▁▂▃▄▅▆▇█▏▎▍▌▋▊▉·•◉◼◻✔✻❯>\-=_~*#|]+$")


def sh(args: list[str]) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""


# ---------------------------------------------------------------- tmux 상태 읽기


def tmux_windows(session: str) -> list[dict]:
    fmt = "#{window_index}\t#{window_name}\t#{pane_tty}\t#{pane_current_path}"
    out = sh(["tmux", "list-windows", "-t", session, "-F", fmt])
    windows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        idx, name, tty, path = parts
        windows.append({"index": int(idx), "name": name, "tty": tty, "cwd": path})
    return windows


def claude_proc_on_tty(tty: str) -> tuple[int, list[str]] | None:
    """그 tty 에 붙어있는 claude 프로세스의 (pid, argv).

    pane_pid 의 자식만 보면 놓친다(창에 따라 claude 가 재-부모화된다). tty 기준이 확실하다.
    MCP 헬퍼(node ...)가 같은 tty 에 붙으므로 실행파일명이 claude 인 것만 고른다.
    pid 는 스냅샷 사이에 "같은 프로세스인가"를 판정하는 데 쓴다(아래 merge_ledger).
    """
    out = sh(["ps", "-t", tty.replace("/dev/", ""), "-o", "pid=,args="])
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        pid, argv = int(parts[0]), parts[1:]
        if os.path.basename(argv[0]).startswith("claude"):
            return pid, argv
    return None


def claude_argv_on_tty(tty: str) -> list[str] | None:
    proc = claude_proc_on_tty(tty)
    return proc[1] if proc else None


def capture_pane(session: str, index: int) -> str:
    """🚨 보이는 화면만 잡는다 — `-S -N` 을 주면 안 된다.

    Claude 는 alternate screen(전체화면 TUI)에서 돈다. alternate screen 에는 히스토리가
    없어서 `-S -400` 을 주면 tmux 가 그 이전 **일반 화면의 옛 스크롤백**을 돌려준다.
    그건 지금 대화와 무관한 내용이라 지문이 통째로 오염된다(실제로 그렇게 0점이 나왔다).
    """
    return sh(["tmux", "capture-pane", "-p", "-t", f"{session}:{index}"])


# ------------------------------------------------------- 세션 ID 해석 (확정/추론)


def id_from_argv(argv: list[str]) -> str | None:
    for i, tok in enumerate(argv):
        if tok in SESSION_FLAGS_WITH_VALUE and i + 1 < len(argv):
            if UUID_RE.fullmatch(argv[i + 1]):
                return argv[i + 1]
        if "=" in tok:
            flag, _, val = tok.partition("=")
            if flag in SESSION_FLAGS_WITH_VALUE and UUID_RE.fullmatch(val):
                return val
    return None


def project_dir_for(cwd: str) -> Path:
    return PROJECTS / re.sub(r"[/.]", "-", cwd)


_NOISE = re.compile(r"[\s*_`~#\\\-–—>|·•]+")


def norm(s: str) -> str:
    """화면(렌더된 마크다운)과 세션 파일(원문 JSON)을 같은 평면으로 눕힌다.

    화면에는 `**굵게**` 가 굵게 렌더돼 별표가 없고, 폭에서 줄바꿈되며, UI 들여쓰기가 붙는다.
    파일에는 별표와 `\\n` 이스케이프가 그대로 있다. 양쪽에서 공백/강조기호/역슬래시를
    싹 걷어내면 남는 글자열이 일치한다.
    """
    return _NOISE.sub("", s)


def fingerprint_lines(pane_text: str, want: int = 14) -> list[str]:
    """화면에서 '대화 내용'으로 보이는 줄만 추린다 — 세션 파일 대조용 지문."""
    seen, picked = set(), []
    for raw in pane_text.splitlines():
        s = raw.strip()
        if len(s) < 30 or BOXY.match(s):
            continue
        # UI 장식/경로/프롬프트 줄은 지문으로 쓰지 않는다
        if s.startswith(("❯", "$", "direnv:", "http://", "https://")):
            continue
        s = s.strip("│┃|· ")
        if len(s) < 30 or s in seen:
            continue
        seen.add(s)
        picked.append(s)
    picked.sort(key=len, reverse=True)
    return picked[:want]


def _candidate_files(cwd: str, max_candidates: int) -> tuple[list[Path], str]:
    """1순위 = 그 cwd 의 프로젝트 디렉터리. 비면 최근 수정된 전체 세션으로 넓힌다.

    넓히는 이유: 세션 도중 cwd 가 바뀌면(워크트리 진입 등) 창의 cwd 와 세션이 저장된
    디렉터리가 어긋난다. 지문 대조가 어차피 정답을 가려주므로 후보를 넓혀도 안전하다.
    """
    pdir = project_dir_for(cwd)
    if pdir.is_dir():
        files = sorted(pdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            return files[:max_candidates], "cwd 프로젝트"
    recent = sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return recent[: max_candidates * 4], "전체 최근 세션"


def infer_session_id(cwd: str, pane_text: str, max_candidates: int = 10) -> tuple[str | None, str]:
    """화면 내용이 가장 많이 들어있는 세션 파일을 고른다. → (id, 설명)"""
    files, scope = _candidate_files(cwd, max_candidates)
    if not files:
        return None, "세션 파일 없음"

    # 그 cwd 에 세션이 하나뿐이면 헷갈릴 여지가 없다 — 내용 대조 없이 확정.
    if scope == "cwd 프로젝트" and len(files) == 1:
        return files[0].stem, "cwd 에 세션이 1개뿐 (모호성 없음)"

    probes = [norm(p)[:40] for p in fingerprint_lines(pane_text)]
    probes = [p for p in probes if len(p) >= 20]
    if len(probes) < 2:
        return None, "화면에서 지문을 못 뽑음"

    scores = []
    for f in files:
        try:
            body = norm(f.read_text(errors="ignore"))
        except Exception:
            continue
        scores.append((sum(1 for p in probes if p in body), f))
    if not scores:
        return None, "세션 파일을 읽지 못함"

    scores.sort(key=lambda t: t[0], reverse=True)
    best_hits, best = scores[0]
    runner = scores[1][0] if len(scores) > 1 else 0
    if best_hits == 0 or best_hits == runner:
        return None, f"판별 불가 (최고 {best_hits}점, 차점 {runner}점 — 애매하면 기록하지 않는다)"
    weak = " ⚠︎단독일치" if best_hits == 1 else ""
    return best.stem, f"{scope} 대조 {best_hits}/{len(probes)}점 (차점 {runner}){weak}"


def model_from_session(cwd: str, session_id: str) -> str | None:
    """세션 파일 끝에서 마지막으로 쓴 모델을 읽는다(사용자가 --model 없이 띄웠을 때 보정)."""
    f = project_dir_for(cwd) / f"{session_id}.jsonl"
    if not f.is_file():
        return None
    try:
        lines = f.read_text(errors="ignore").splitlines()
    except Exception:
        return None
    for line in reversed(lines[-400:]):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        model = (obj.get("message") or {}).get("model") if isinstance(obj.get("message"), dict) else None
        if isinstance(model, str) and model.startswith("claude"):
            return model
    return None


# ------------------------------------------------------------------- 커맨드 복원


def restore_command(entry: dict) -> str | None:
    """원장 항목 → 실행할 셸 커맨드. 세션 ID 를 못 찾았으면 None."""
    argv = list(entry.get("argv") or [])
    if not argv:
        return None

    cleaned, skip = [], False
    for tok in argv:
        if skip:
            skip = False
            continue
        flag = tok.partition("=")[0]
        if flag in SESSION_FLAGS_WITH_VALUE:
            skip = "=" not in tok
            continue
        if tok in SESSION_FLAGS_BARE:
            continue
        cleaned.append(tok)

    sid = entry.get("session_id")
    if not sid:
        return None
    cleaned += ["--resume", sid]

    if "--model" not in cleaned and entry.get("model"):
        cleaned += ["--model", entry["model"]]

    return " ".join(quote(t) for t in cleaned)


def quote(tok: str) -> str:
    return tok if re.fullmatch(r"[A-Za-z0-9._/=:@-]+", tok) else "'" + tok.replace("'", "'\\''") + "'"


# ------------------------------------------------------------------- 서브커맨드


def cmd_snapshot(args) -> int:
    windows = tmux_windows(args.session)
    if not windows:
        print(f"tmux 세션 '{args.session}' 이 없습니다.", file=sys.stderr)
        return 1

    entries = []
    for w in windows:
        proc = claude_proc_on_tty(w["tty"])
        pid, argv = proc if proc else (None, None)
        entry = {
            "index": w["index"],
            "name": w["name"],
            "cwd": w["cwd"],
            "alive": argv is not None,
            "pid": pid,
            "argv": argv,
            "session_id": None,
            "model": None,
            "source": None,
        }
        if argv:
            sid = id_from_argv(argv)
            if sid:
                entry["session_id"], entry["source"] = sid, "argv"
            else:
                sid, why = infer_session_id(w["cwd"], capture_pane(args.session, w["index"]))
                entry["session_id"] = sid
                entry["source"] = f"추론: {why}"
            if entry["session_id"]:
                entry["model"] = next(
                    (argv[i + 1] for i, t in enumerate(argv) if t == "--model" and i + 1 < len(argv)),
                    None,
                ) or model_from_session(w["cwd"], entry["session_id"])
        entries.append(entry)

    # 같은 세션 ID 가 두 창에 배정되면 둘 중 하나는 반드시 틀렸다 — 둘 다 버린다.
    # (mtime 만 보고 고르다 같은 cwd 의 두 창을 뒤바꾼 사고가 이 스킬을 만든 계기다.)
    claimed: dict[str, list[dict]] = {}
    for e in entries:
        if e["session_id"] and e["source"] != "argv":
            claimed.setdefault(e["session_id"], []).append(e)
    for sid, owners in claimed.items():
        if len(owners) > 1:
            for e in owners:
                e["session_id"] = None
                e["source"] = f"충돌: {sid[:8]} 를 여러 창이 주장 — 기록 보류"

    prev = load_ledger()
    merged = merge_ledger(prev, entries)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)
    payload = {"session": args.session, "saved_at": int(time.time()), "windows": merged}
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(LEDGER)
    shutil.copy2(LEDGER, HISTORY / f"ledger-{payload['saved_at']}.json")
    for old in sorted(HISTORY.glob("ledger-*.json"))[:-HISTORY_KEEP]:
        old.unlink(missing_ok=True)

    for e in merged:
        mark = "live" if e["alive"] else "dead"
        sid = e["session_id"] or "—"
        print(f"  [{mark:>4}] {e['index']} {e['name'][:38]:<38} {sid[:8]}  {e.get('source') or ''}")
    print(f"원장 기록: {LEDGER}")
    return 0


def merge_ledger(prev: dict | None, entries: list[dict]) -> list[dict]:
    """원장은 절대 나빠지지 않아야 한다 — 알아낸 것을 되돌리지 않는다.

    두 가지를 물려받는다:
      · 죽은 창의 정보 전부 — 죽고 나면 알아낼 방법이 없다.
      · 살아있지만 이번에 ID 를 못 알아낸 창의 ID — **단, 같은 프로세스일 때만**.
        추론은 그때 화면에 무엇이 떠 있었는지에 좌우돼서, 한 번 8/14점으로 맞춘 창이
        다음 스냅샷엔 0점이 나올 수 있다. 그때마다 ID 를 버리면 원장이 시간이 갈수록
        나빠진다. pid 가 그대로면 문자 그대로 같은 claude 프로세스 = 같은 세션이므로
        물려받아도 안전하고, pid 가 바뀌었으면(사용자가 껐다 켬) 물려받지 않는다.
    """
    old = {e["index"]: e for e in (prev or {}).get("windows", [])}
    out = []
    for e in entries:
        prev_e = old.get(e["index"])
        if not e["alive"] and prev_e:
            keep = dict(prev_e)
            keep["alive"] = False
            keep["name"] = e["name"] or keep.get("name")
            keep["cwd"] = e["cwd"] or keep.get("cwd")
            out.append(keep)
            continue
        if (
            e["alive"]
            and not e["session_id"]
            and prev_e
            and prev_e.get("session_id")
            and prev_e.get("pid") is not None
            and prev_e.get("pid") == e.get("pid")
        ):
            e = dict(e)
            e["session_id"] = prev_e["session_id"]
            e["model"] = e.get("model") or prev_e.get("model")
            e["source"] = f"이전 스냅샷 유지 (같은 pid {e['pid']})"
        out.append(e)
    return out


def load_ledger() -> dict | None:
    if not LEDGER.is_file():
        return None
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return None


def was_claude_window(entry: dict) -> bool:
    """이 창에서 claude 를 본 적이 있는가.

    nydus 에는 claude 가 아닌 상시 프로세스 창도 있다(m4-mini 의 `python -m nao.bot` 등).
    그런 창은 claude 가 없다고 해서 '죽은' 게 아니므로 복구 대상이 아니다.
    """
    return bool(entry.get("argv"))


def cmd_status(args) -> int:
    led = load_ledger()
    if not led:
        print("원장이 없습니다. 먼저 `snapshot` 을 돌리세요.", file=sys.stderr)
        return 1
    age = int(time.time()) - led.get("saved_at", 0)
    print(f"원장: {LEDGER}  ({age // 60}분 전 기록, 세션={led.get('session')})")
    live = {w["index"]: claude_argv_on_tty(w["tty"]) is not None for w in tmux_windows(led.get("session", args.session))}
    dead = unknown = 0
    for e in led["windows"]:
        now = live.get(e["index"])
        if now is None:
            state = "창 없음"
        elif now:
            state = "정상"
        elif not was_claude_window(e):
            state = "claude 창 아님 — 대상 아님"
        elif e.get("session_id"):
            state, dead = "죽음 → 복구 대상", dead + 1
        else:
            state, unknown = "죽음 — ⚠︎ 세션 ID 미상, 수동 확인 필요", unknown + 1
        print(f"  {e['index']} {e['name'][:38]:<38} {(e['session_id'] or '—')[:8]}  {state}")
    tail = f"복구 대상 {dead}개"
    if unknown:
        tail += f" / ID 미상 {unknown}개"
    print(tail)
    return 0


def cmd_restore(args) -> int:
    led = load_ledger()
    if not led:
        print("원장이 없습니다. 복구할 수 없습니다.", file=sys.stderr)
        return 1
    session = led.get("session", args.session)
    current = {w["index"]: w for w in tmux_windows(session)}
    if not current:
        print(f"tmux 세션 '{session}' 이 없습니다.", file=sys.stderr)
        return 1

    acted = skipped = failed = 0
    for e in led["windows"]:
        idx = e["index"]
        if args.window is not None and idx != args.window:
            continue
        w = current.get(idx)
        if not w:
            print(f"  [건너뜀] {idx} {e['name']} — 창이 없습니다")
            skipped += 1
            continue
        if claude_argv_on_tty(w["tty"]) is not None:
            print(f"  [건너뜀] {idx} {e['name']} — 이미 살아있음 (절대 건드리지 않음)")
            skipped += 1
            continue

        if not was_claude_window(e):
            print(f"  [건너뜀] {idx} {e['name']} — claude 창이 아닙니다 (복구 대상 아님)")
            skipped += 1
            continue

        cmd = restore_command(e)
        if not cmd:
            print(f"  [실패]   {idx} {e['name']} — 세션 ID 를 모릅니다 (원장에 없음). 수동 확인 필요")
            failed += 1
            continue

        print(f"  [{'예정' if args.dry_run else '복구'}]   {idx} {e['name']}\n            {cmd}")
        if not args.dry_run:
            subprocess.run(["tmux", "send-keys", "-t", f"{session}:{idx}", "C-u", cmd, "Enter"])
            acted += 1
            time.sleep(1.5)  # 동시에 여러 개 띄우면 첫 렌더가 엉킨다

    print(f"복구 {acted} / 건너뜀 {skipped} / 실패 {failed}")
    return 0 if failed == 0 else 2


HOOK_LINE = (
    "set -g @resurrect-hook-post-save-all "
    "'~/.claude/skills/nydus-revive/scripts/nydus_sessions.py snapshot >/dev/null 2>&1'"
)


TPM_RUN = "run '~/.tmux/plugins/tpm/tpm'"


def chezmoi_source_of(path: Path) -> str | None:
    """chezmoi 가 관리하는 파일이면 그 소스 경로. 아니면 None."""
    if not shutil.which("chezmoi"):
        return None
    r = subprocess.run(
        ["chezmoi", "source-path", str(path)], capture_output=True, text=True, timeout=20
    )
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def cmd_install_hook(args) -> int:
    conf = Path.home() / ".tmux.conf"
    text = conf.read_text() if conf.is_file() else ""

    if "@resurrect-hook-post-save-all" in text:
        print("이미 배선돼 있습니다:")
        for line in text.splitlines():
            if "@resurrect-hook-post-save-all" in line:
                print("  " + line.strip())
        return 0

    # 🚨 chezmoi 관리 파일이면 타겟을 직접 고치지 않는다 — 다음 apply 때 되돌아가거나
    #    영구 드리프트가 된다. 소스(템플릿)를 고치는 게 정본 경로다.
    src = chezmoi_source_of(conf)
    if src:
        print(f"{conf} 는 chezmoi 관리 파일입니다 (소스: {src}).")
        print("타겟을 직접 고치지 않습니다. 소스에 아래 줄을 넣고 `chezmoi apply` 하세요 —")
        print(f"위치는 resurrect 설정들 바로 뒤, `{TPM_RUN}` **앞**입니다(TPM 은 맨 마지막 줄 규칙).")
        print("  " + HOOK_LINE)
        return 1

    block = f"\n# nydus-revive — resurrect 저장마다 Claude 세션 원장도 갱신\n{HOOK_LINE}\n"
    if args.dry_run:
        print("추가할 내용:" + block)
        return 0

    # TPM 초기화는 반드시 맨 마지막 줄이어야 하므로 그 앞에 끼워 넣는다.
    if TPM_RUN in text:
        text = text.replace(TPM_RUN, block.lstrip("\n") + "\n" + TPM_RUN, 1)
    else:
        text = text + block
    conf.write_text(text)
    subprocess.run(["tmux", "source-file", str(conf)])
    print(f"{conf} 에 배선했습니다. resurrect 저장(continuum 기본 15분)마다 원장이 갱신됩니다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default="nydus", help="대상 tmux 세션 (기본: nydus)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("snapshot", help="살아있는 창의 세션 ID 를 원장에 기록")
    sub.add_parser("status", help="원장 대비 현재 상태 비교")

    r = sub.add_parser("restore", help="죽은 창만 중단 시점으로 되살림")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--window", type=int, default=None)

    h = sub.add_parser("install-hook", help="continuum 저장 훅에 snapshot 배선")
    h.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()
    return {
        "snapshot": cmd_snapshot,
        "status": cmd_status,
        "restore": cmd_restore,
        "install-hook": cmd_install_hook,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
