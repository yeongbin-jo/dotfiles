#!/usr/bin/env python3
"""nydus tmux 세션의 Claude Code / Codex 창을 중단 시점 그대로 되살린다.

배경
----
이 맥에는 tmux-resurrect + continuum 이 깔려 있어(15분 자동저장, 서버 시작 시 자동복원)
강제종료/배터리 방전 뒤에도 **창·cwd·스크롤백은** 돌아온다. 그런데 resurrect 가 되살리는
프로그램은 `@resurrect-processes` 화이트리스트뿐이라 **claude/codex 프로세스는 살아나지 않고
맨 셸만 남는다.** 이 스크립트가 그 빈칸을 메운다.

핵심 문제는 "어느 창이 어느 대화였는가" 다. 죽은 뒤에 추측하면 틀린다(mtime 순서로
고르면 같은 cwd 를 쓰는 창끼리 뒤바뀐다 — 실제로 그렇게 한 번 틀렸다). 그래서 이 스크립트는
**살아있을 때 원장(ledger)을 남겨두고**, 복구는 그 원장을 재생하기만 한다.

세션 ID 해석 순서:
  claude
    1. argv 의 `--resume/-r <id>` 또는 `--session-id <id>`  ← 시작 시점 기준 확정
    2. 창의 화면 내용을 그 cwd 의 세션 파일들과 대조해 추론 (argv 와 다르면 화면 우선)
  codex
    1. lsof — codex 는 자기 rollout 파일을 열어둔 채로 돈다. 그 경로의 UUID 가 **지금** 세션.
       (argv 보다 확실하다: /new 로 갈아타도 열린 파일이 따라간다)
    2. argv 의 `resume <id>`
    3. 화면 내용을 최근 rollout 파일들과 대조해 추론

사용법:
  nydus_sessions.py snapshot          # 원장 기록 (살아있을 때, 주기적으로)
  nydus_sessions.py status            # 원장 vs 현재 상태 비교 (죽은 창 표시)
  nydus_sessions.py restore [--dry-run] [--window N] [--include-exited]
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
CODEX_SESSIONS = Path.home() / ".codex/sessions"
CODEX_RECENT = 60  # 화면 대조 후보로 살펴볼 최근 rollout 개수

# claude argv 에서 세션을 고르는 플래그 — 복구 커맨드를 만들 때 전부 걷어내고 --resume 로 통일한다.
SESSION_FLAGS_WITH_VALUE = {"--resume", "-r", "--session-id"}
SESSION_FLAGS_BARE = {"--continue", "-c", "--fork-session"}

# codex 전역 플래그 중 값을 하나 받는 것 — 복구 커맨드에서 값까지 같이 보존한다.
CODEX_FLAGS_WITH_VALUE = {
    "-m", "--model", "-c", "--config", "-p", "--profile", "-s", "--sandbox",
    "-a", "--ask-for-approval", "-C", "--cd", "-i", "--image", "--enable", "--disable",
    "--add-dir", "--remote",
}
# codex 서브커맨드 — resume 만 되살릴 수 있다 (exec/apply 등은 대화가 아니다).
CODEX_SUBCOMMANDS = {
    "exec", "e", "review", "login", "logout", "mcp", "mcp-server", "app-server", "apply", "a",
    "cloud", "sandbox", "debug", "completion", "features", "resume", "fork", "generate-ts",
}

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
ROLLOUT_RE = re.compile(r"rollout-.*-(" + UUID_RE.pattern + r")\.jsonl$")
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


def tmux_start_time() -> int | None:
    """tmux 서버가 뜬 시각(epoch). 마지막 원장보다 늦으면 그 사이 서버가 죽었다 살아난 것."""
    out = sh(["tmux", "display", "-p", "#{start_time}"]).strip()
    return int(out) if out.isdigit() else None


def agent_kind(argv0: str) -> str | None:
    """실행파일명으로 어떤 에이전트인지. claude / codex / None.

    codex 는 같은 tty 에 `codex-code-mode-host` 같은 헬퍼를 붙이므로 **정확히** codex 여야 한다.
    """
    base = os.path.basename(argv0)
    if base.startswith("claude"):
        return "claude"
    if base == "codex":
        return "codex"
    return None


def agent_proc_on_tty(tty: str) -> tuple[str, int, list[str]] | None:
    """그 tty 에 붙어있는 claude/codex 프로세스의 (kind, pid, argv).

    pane_pid 의 자식만 보면 놓친다(창에 따라 재-부모화된다). tty 기준이 확실하다.
    MCP 헬퍼(node ...)가 같은 tty 에 붙으므로 실행파일명으로 고른다.
    pid 는 스냅샷 사이에 "같은 프로세스인가"를 판정하는 데 쓴다(아래 merge_ledger).
    """
    out = sh(["ps", "-t", tty.replace("/dev/", ""), "-o", "pid=,args="])
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        pid, argv = int(parts[0]), parts[1:]
        kind = agent_kind(argv[0])
        if kind:
            return kind, pid, argv
    return None


def agent_alive_on_tty(tty: str) -> bool:
    return agent_proc_on_tty(tty) is not None


def capture_pane(session: str, index: int) -> str:
    """🚨 보이는 화면만 잡는다 — `-S -N` 을 주면 안 된다.

    Claude/Codex 는 alternate screen(전체화면 TUI)에서 돈다. alternate screen 에는 히스토리가
    없어서 `-S -400` 을 주면 tmux 가 그 이전 **일반 화면의 옛 스크롤백**을 돌려준다.
    그건 지금 대화와 무관한 내용이라 지문이 통째로 오염된다(실제로 그렇게 0점이 나왔다).
    """
    return sh(["tmux", "capture-pane", "-p", "-t", f"{session}:{index}"])


# ------------------------------------------------------- 세션 ID 해석 (확정/추론)


def id_from_argv(argv: list[str]) -> str | None:
    """claude: --resume/-r/--session-id <uuid>."""
    for i, tok in enumerate(argv):
        if tok in SESSION_FLAGS_WITH_VALUE and i + 1 < len(argv):
            if UUID_RE.fullmatch(argv[i + 1]):
                return argv[i + 1]
        if "=" in tok:
            flag, _, val = tok.partition("=")
            if flag in SESSION_FLAGS_WITH_VALUE and UUID_RE.fullmatch(val):
                return val
    return None


def codex_id_from_argv(argv: list[str]) -> str | None:
    """codex: `resume <uuid>` (`resume --last` 는 어느 세션인지 argv 로는 모른다)."""
    for i, tok in enumerate(argv):
        if tok == "resume":
            for nxt in argv[i + 1:]:
                if UUID_RE.fullmatch(nxt):
                    return nxt
            return None
    return None


def codex_id_from_lsof(pid: int) -> str | None:
    """codex 프로세스가 열어둔 rollout 파일의 UUID — 지금 진행 중인 세션의 확정 근거.

    (2026-09-06 실측: `lsof -p <pid>` 에 `~/.codex/sessions/.../rollout-...-<uuid>.jsonl` 이
    fd 로 잡혀 있었다. claude 는 파일을 열어두지 않아서 이 방법이 안 통한다.)
    """
    out = sh(["lsof", "-p", str(pid), "-Fn"])
    for line in out.splitlines():
        if line.startswith("n") and "/.codex/sessions/" in line:
            m = ROLLOUT_RE.search(line)
            if m:
                return m.group(1)
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
        if s.startswith(("❯", "›", "$", "direnv:", "http://", "https://")):
            continue
        s = s.strip("│┃|· ")
        if len(s) < 30 or s in seen:
            continue
        seen.add(s)
        picked.append(s)
    picked.sort(key=len, reverse=True)
    return picked[:want]


def _candidate_files(cwd: str, max_candidates: int) -> tuple[list[Path], str]:
    """claude: 1순위 = 그 cwd 의 프로젝트 디렉터리. 비면 최근 수정된 전체 세션으로 넓힌다.

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


def _rollout_cwd(f: Path) -> str | None:
    """rollout 첫 줄(session_meta)의 cwd."""
    try:
        with f.open(encoding="utf-8", errors="ignore") as fh:
            first = fh.readline()
        obj = json.loads(first)
        if obj.get("type") == "session_meta":
            return (obj.get("payload") or {}).get("cwd")
    except Exception:
        pass
    return None


def _codex_candidate_files(cwd: str) -> tuple[list[Path], str]:
    """codex: 최근 rollout 중 session_meta.cwd 가 창의 cwd 와 같은 것. 없으면 최근 전체."""
    if not CODEX_SESSIONS.is_dir():
        return [], "rollout 없음"
    recent = sorted(CODEX_SESSIONS.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    recent = recent[:CODEX_RECENT]
    same = [f for f in recent if _rollout_cwd(f) == cwd]
    if same:
        return same, "cwd rollout"
    return recent, "전체 최근 rollout"


def _session_id_of(f: Path) -> str:
    m = ROLLOUT_RE.search(f.name)
    return m.group(1) if m else f.stem


def _score_files(files: list[Path], scope: str, pane_text: str, single_ok: bool) -> tuple[str | None, str]:
    if not files:
        return None, "세션 파일 없음"

    # 후보가 하나뿐이면 헷갈릴 여지가 없다 — 내용 대조 없이 확정. (cwd 범위일 때만)
    if single_ok and len(files) == 1:
        return _session_id_of(files[0]), f"{scope} 에 세션이 1개뿐 (모호성 없음)"

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
    return _session_id_of(best), f"{scope} 대조 {best_hits}/{len(probes)}점 (차점 {runner}){weak}"


def infer_session_id(cwd: str, pane_text: str, max_candidates: int = 10) -> tuple[str | None, str]:
    """claude: 화면 내용이 가장 많이 들어있는 세션 파일을 고른다. → (id, 설명)"""
    files, scope = _candidate_files(cwd, max_candidates)
    return _score_files(files, scope, pane_text, single_ok=(scope == "cwd 프로젝트"))


def infer_codex_session_id(cwd: str, pane_text: str) -> tuple[str | None, str]:
    """codex: lsof/argv 가 다 실패했을 때의 폴백 — 화면 대조."""
    files, scope = _codex_candidate_files(cwd)
    return _score_files(files, scope, pane_text, single_ok=(scope == "cwd rollout"))


def model_from_session(cwd: str, session_id: str) -> str | None:
    """claude 세션 파일 끝에서 마지막으로 쓴 모델을 읽는다(--model 없이 띄웠을 때 보정).

    codex 는 모델이 ~/.codex/config.toml 기본값을 따르므로 argv 의 -m 만 보존하고 보정하지 않는다.
    """
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


def entry_kind(entry: dict) -> str:
    """옛 원장(kind 없음)은 전부 claude 였다."""
    return entry.get("kind") or "claude"


def restore_command(entry: dict) -> str | None:
    """원장 항목 → 실행할 셸 커맨드. 세션 ID 를 못 찾았으면 None."""
    argv = list(entry.get("argv") or [])
    sid = entry.get("session_id")
    if not argv or not sid:
        return None
    if entry_kind(entry) == "codex":
        return codex_restore_command(argv, sid)

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

    cleaned += ["--resume", sid]

    if "--model" not in cleaned and entry.get("model"):
        cleaned += ["--model", entry["model"]]

    return " ".join(quote(t) for t in cleaned)


def codex_restore_command(argv: list[str], sid: str) -> str | None:
    """`codex [전역플래그] [resume <id>|<prompt>]` → `codex [전역플래그] resume <sid>`.

    전역 플래그(--dangerously-bypass-approvals-and-sandbox, -m, -c … )는 그대로 보존하고,
    서브커맨드/세션 ID/프롬프트 위치인자는 걷어낸다. resume 이 아닌 서브커맨드(exec 등)로
    띄운 창은 대화가 아니므로 되살리지 않는다.
    """
    head, rest = argv[0], argv[1:]
    flags, skip = [], False
    for i, tok in enumerate(rest):
        if skip:
            flags.append(tok)
            skip = False
            continue
        if tok.startswith("-"):
            flags.append(tok)
            skip = tok in CODEX_FLAGS_WITH_VALUE
            continue
        if tok in CODEX_SUBCOMMANDS:
            if tok not in ("resume", "fork"):
                return None
            # resume 뒤의 옵션(--last/--all …)과 ID/프롬프트는 전부 버린다
            break
        # 위치인자(프롬프트) — 버린다
    return " ".join(quote(t) for t in [head, *flags, "resume", sid])


def quote(tok: str) -> str:
    return tok if re.fullmatch(r"[A-Za-z0-9._/=:@-]+", tok) else "'" + tok.replace("'", "'\\''") + "'"


# ------------------------------------------------------------------- 서브커맨드


def _resolve_claude(entry: dict, session: str, w: dict, argv: list[str]) -> None:
    sid = id_from_argv(argv)
    if sid:
        # argv 의 --resume <id> 는 "시작할 때" 의 세션일 뿐이다. claude 안에서
        # `/resume` 으로 갈아타면 argv 는 옛 ID 그대로 남는다 — 2026-08-23 실제로
        # 두 창이 그 상태였고, 원장이 옛 세션을 "확정"으로 기록해 복구가 틀렸다.
        # 그래서 argv 가 있어도 화면 지문을 대조해, 화면이 **다른** 세션을 확실히
        # 가리키면(동점·0점 아님) 화면 쪽을 믿는다. 판별 불가면 argv 유지.
        entry["session_id"], entry["source"] = sid, "argv"
        screen_sid, why = infer_session_id(w["cwd"], capture_pane(session, w["index"]))
        if screen_sid and screen_sid != sid:
            entry["session_id"] = screen_sid
            entry["source"] = f"화면 우선(argv {sid[:8]} 와 불일치 — /resume 갈아탐?): {why}"
    else:
        sid, why = infer_session_id(w["cwd"], capture_pane(session, w["index"]))
        entry["session_id"] = sid
        entry["source"] = f"추론: {why}"
    if entry["session_id"]:
        entry["model"] = next(
            (argv[i + 1] for i, t in enumerate(argv) if t == "--model" and i + 1 < len(argv)),
            None,
        ) or model_from_session(w["cwd"], entry["session_id"])


def _resolve_codex(entry: dict, session: str, w: dict, pid: int, argv: list[str]) -> None:
    sid = codex_id_from_lsof(pid)
    if sid:
        entry["session_id"], entry["source"] = sid, "lsof(열린 rollout)"
    else:
        sid = codex_id_from_argv(argv)
        if sid:
            entry["session_id"], entry["source"] = sid, "argv (lsof 실패 — /new 갈아탔으면 틀릴 수 있음)"
        else:
            sid, why = infer_codex_session_id(w["cwd"], capture_pane(session, w["index"]))
            entry["session_id"] = sid
            entry["source"] = f"추론: {why}"
    if entry["session_id"]:
        entry["model"] = next(
            (argv[i + 1] for i, t in enumerate(argv) if t in ("-m", "--model") and i + 1 < len(argv)),
            None,
        )


def cmd_snapshot(args) -> int:
    windows = tmux_windows(args.session)
    if not windows:
        print(f"tmux 세션 '{args.session}' 이 없습니다.", file=sys.stderr)
        return 1

    entries = []
    for w in windows:
        proc = agent_proc_on_tty(w["tty"])
        kind, pid, argv = proc if proc else (None, None, None)
        entry = {
            "index": w["index"],
            "name": w["name"],
            "cwd": w["cwd"],
            "alive": argv is not None,
            "kind": kind,
            "pid": pid,
            "argv": argv,
            "session_id": None,
            "model": None,
            "source": None,
            "exited_at": None,
        }
        if kind == "claude":
            _resolve_claude(entry, args.session, w, argv)
        elif kind == "codex":
            _resolve_codex(entry, args.session, w, pid, argv)
        entries.append(entry)

    # 같은 세션 ID 가 두 창에 배정되면 둘 중 하나는 반드시 틀렸다 — 둘 다 버린다.
    # (mtime 만 보고 고르다 같은 cwd 의 두 창을 뒤바꾼 사고가 이 스킬을 만든 계기다.)
    # 확정 근거(argv/lsof)로 잡힌 건 예외 — 같은 대화를 두 창에서 정말로 열어둔 것이다.
    claimed: dict[str, list[dict]] = {}
    for e in entries:
        if e["session_id"] and not (e["source"] or "").startswith(("argv", "lsof")):
            claimed.setdefault(e["session_id"], []).append(e)
    for sid, owners in claimed.items():
        if len(owners) > 1:
            for e in owners:
                e["session_id"] = None
                e["source"] = f"충돌: {sid[:8]} 를 여러 창이 주장 — 기록 보류"

    prev = load_ledger()
    # tmux 서버가 마지막 원장 이후에 떴으면 그 사이 크래시/재시작이 있었던 것 — 창들이
    # 죽어 있는 건 사용자가 닫은 게 아니므로 exited_at 을 찍으면 안 된다.
    start = tmux_start_time()
    restarted = bool(prev and start and start > prev.get("saved_at", 0))
    merged = merge_ledger(prev, entries, restarted=restarted)

    # 죽은 창이 물려받은 기록이 **살아있는 다른 창**의 프로세스/세션을 가리키면 그건 허깨비다.
    # 원장은 창 번호로 물려받는데, 창이 새로 생기거나 번호가 밀리면 옛 index N 의 기록이
    # 전혀 다른 창에 영원히 눌러앉는다. 2026-08-26 창5(codex)가 창4(claude)의 pid 69368 과
    # 세션 9db31d94 를 그렇게 물려받아, 복구했으면 같은 대화가 두 창에 뜰 뻔했다.
    # 살아있는 프로세스가 언제나 정답이므로 죽은 쪽 기록을 버린다.
    live_pids = {e.get("pid") for e in merged if e["alive"] and e.get("pid")}
    live_sids = {e.get("session_id") for e in merged if e["alive"] and e.get("session_id")}
    for e in merged:
        if e["alive"]:
            continue
        if (e.get("pid") and e["pid"] in live_pids) or (
            e.get("session_id") and e["session_id"] in live_sids
        ):
            stale = e.get("session_id")
            e["pid"] = e["session_id"] = e["model"] = e["argv"] = e["kind"] = None
            e["source"] = (
                f"물려받은 기록 폐기 — {(stale or '?')[:8]} 는 살아있는 다른 창의 것 "
                "(창 번호 밀림). 이 창이 무엇이었는지 사람이 확인해야 함"
            )

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
        kind = (e.get("kind") or "-")[:6]
        extra = f"  (종료 {fmt_ts(e['exited_at'])})" if e.get("exited_at") else ""
        print(f"  [{mark:>4}] {e['index']} {e['name'][:38]:<38} {kind:<6} {sid[:8]}  {e.get('source') or ''}{extra}")
    if restarted:
        print("  (tmux 서버가 마지막 원장 이후 재시작됨 — 죽은 창을 '사용자 종료'로 기록하지 않음)")
    print(f"원장 기록: {LEDGER}")
    return 0


def fmt_ts(ts: int | None) -> str:
    return time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "?"


def merge_ledger(prev: dict | None, entries: list[dict], restarted: bool = False) -> list[dict]:
    """원장은 절대 나빠지지 않아야 한다 — 알아낸 것을 되돌리지 않는다.

    두 가지를 물려받는다:
      · 죽은 창의 정보 전부 — 죽고 나면 알아낼 방법이 없다.
      · 살아있지만 이번에 ID 를 못 알아낸 창의 ID — **단, 같은 프로세스일 때만**.
        추론은 그때 화면에 무엇이 떠 있었는지에 좌우돼서, 한 번 8/14점으로 맞춘 창이
        다음 스냅샷엔 0점이 나올 수 있다. 그때마다 ID 를 버리면 원장이 시간이 갈수록
        나빠진다. pid 가 그대로면 문자 그대로 같은 프로세스 = 같은 세션이므로
        물려받아도 안전하고, pid 가 바뀌었으면(사용자가 껐다 켬) 물려받지 않는다.

    exited_at: 지난 스냅샷엔 살아있던 프로세스가 **tmux 서버는 그대로인데** 사라졌으면
    사용자가 직접 닫은 것이다. 시각을 찍어두고 restore 가 기본으로 건너뛴다.
    (2026-09-05 창4 가 크래시 30분 전에 닫힌 세션이었는데 원장이 그걸 '복구 대상'으로 잡았다.)
    서버가 재시작됐으면(restarted) 죽은 게 크래시 탓이니 찍지 않는다.
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
            keep.setdefault("kind", "claude" if keep.get("argv") else None)
            keep.setdefault("exited_at", None)
            if prev_e.get("alive") and not restarted and not keep["exited_at"]:
                keep["exited_at"] = int(time.time())
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


def was_agent_window(entry: dict) -> bool:
    """이 창에서 claude/codex 를 본 적이 있는가.

    nydus 에는 에이전트가 아닌 상시 프로세스 창도 있다(m4-mini 의 `python -m nao.bot` 등).
    그런 창은 에이전트가 없다고 해서 '죽은' 게 아니므로 복구 대상이 아니다.
    """
    return bool(entry.get("argv"))


def cmd_status(args) -> int:
    led = load_ledger()
    if not led:
        print("원장이 없습니다. 먼저 `snapshot` 을 돌리세요.", file=sys.stderr)
        return 1
    age = int(time.time()) - led.get("saved_at", 0)
    print(f"원장: {LEDGER}  ({age // 60}분 전 기록, 세션={led.get('session')})")
    windows = tmux_windows(led.get("session", args.session))
    live = {w["index"]: agent_alive_on_tty(w["tty"]) for w in windows}
    dead = unknown = exited = 0
    for e in led["windows"]:
        now = live.get(e["index"])
        if now is None:
            state = "창 없음"
        elif now:
            state = "정상"
        elif not was_agent_window(e):
            state = "claude/codex 창 아님 — 대상 아님"
        elif e.get("exited_at"):
            state, exited = f"크래시 전 종료({fmt_ts(e['exited_at'])}) — 기본 제외 (--include-exited)", exited + 1
        elif e.get("session_id"):
            state, dead = "죽음 → 복구 대상", dead + 1
            cur = next((w["cwd"] for w in windows if w["index"] == e["index"]), None)
            if e.get("cwd") and cur and cur != e["cwd"]:
                state += f" (⚠︎ cwd 바뀜: 현재 {cur})"
        else:
            state, unknown = "죽음 — ⚠︎ 세션 ID 미상, 수동 확인 필요", unknown + 1
        kind = (e.get("kind") or ("claude" if e.get("argv") else "-"))[:6]
        print(f"  {e['index']} {e['name'][:38]:<38} {kind:<6} {(e['session_id'] or '—')[:8]}  {state}")
    tail = f"복구 대상 {dead}개"
    if exited:
        tail += f" / 크래시 전 종료 {exited}개"
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
        if agent_alive_on_tty(w["tty"]):
            print(f"  [건너뜀] {idx} {e['name']} — 이미 살아있음 (절대 건드리지 않음)")
            skipped += 1
            continue

        if not was_agent_window(e):
            print(f"  [건너뜀] {idx} {e['name']} — claude/codex 창이 아닙니다 (복구 대상 아님)")
            skipped += 1
            continue

        # 크래시 전에 사용자가 닫은 창은 기본으로 건너뛴다. --window N 으로 콕 집었거나
        # --include-exited 면 되살린다.
        if e.get("exited_at") and not args.include_exited and args.window is None:
            print(
                f"  [건너뜀] {idx} {e['name']} — 크래시 전 {fmt_ts(e['exited_at'])} 에 이미 종료된 창 "
                "(--include-exited 또는 --window 로 지정하면 복구)"
            )
            skipped += 1
            continue

        cmd = restore_command(e)
        if not cmd:
            why = "세션 ID 를 모릅니다 (원장에 없음)" if not e.get("session_id") else "resume 할 수 없는 커맨드"
            print(f"  [실패]   {idx} {e['name']} — {why}. 수동 확인 필요")
            failed += 1
            continue

        # 🚨 창 번호만 믿고 띄우면 안 된다. tmux 서버가 재시작되거나 누가 창에서 cd 하면
        #    같은 번호의 창이 다른 디렉터리를 가리킨다 — 그대로 resume 하면 그 대화가
        #    엉뚱한 폴더에서 열린다(실측: 창 4가 워크트리 대신 ~/project 를 가리켜
        #    Claude 가 폴더 신뢰 프롬프트를 띄웠다).
        # ⚠️ 지역변수 이름에 `current` 를 쓰지 말 것 — 위에서 만든 창 맵(`current`)을 덮어써
        #    다음 순회의 `current.get(idx)` 가 AttributeError 로 죽는다(복구 대상 2개 이상일 때만
        #    드러나는 섀도잉 버그였음).
        recorded, cur_cwd = e.get("cwd"), w["cwd"]
        if recorded and recorded != cur_cwd:
            if not os.path.isdir(recorded):
                print(
                    f"  [실패]   {idx} {e['name']} — 기록된 디렉터리가 없어졌습니다\n"
                    f"            기록: {recorded}\n"
                    f"            현재: {cur_cwd}  ← 어디서 열지 사람이 정해야 합니다"
                )
                failed += 1
                continue
            print(f"            (cwd 불일치 → 기록된 {recorded} 로 이동 후 실행)")
            cmd = f"cd {quote(recorded)} && {cmd}"

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
    r.add_argument("--include-exited", action="store_true", help="크래시 전에 이미 닫힌 창도 되살림")

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
