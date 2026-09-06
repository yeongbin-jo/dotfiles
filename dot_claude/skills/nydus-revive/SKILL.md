---
name: nydus-revive
description: Revive the Claude Code and Codex sessions in this Mac's `nydus` tmux session after a crash, forced shutdown, or battery death — each window resumed at the exact conversation it was interrupted at. Also records the window→session ledger while things are healthy, which is what makes a correct restore possible. Use when tmux windows came back as bare shells, when the user says "nydus 세션 살려줘 / 죽은 탭 되살려 / 세션 복구", or when setting up automatic session persistence.
---

# nydus-revive

`nydus` tmux 세션의 각 창에서 돌던 **Claude Code / Codex 대화를 중단 시점 그대로** 되살린다.

## 왜 필요한가 (이 맥의 정확한 갭)

이 맥에는 tmux-resurrect + continuum 이 깔려 있다 (`~/.tmux.conf`: 15분 자동저장,
`@continuum-restore 'on'`, `@resurrect-capture-pane-contents 'on'`). 그래서 강제종료 뒤에도
**창 구성·cwd·스크롤백은 돌아온다.**

돌아오지 않는 건 프로세스다. resurrect 는 `@resurrect-processes` 화이트리스트에 있는 것만
되살리는데 거기 claude/codex 가 없다 — 그래서 **창은 살아있고 에이전트만 죽어 맨 셸이 남는다.**
이 스킬이 그 빈칸만 정확히 메운다. (2026-09-06 부터 codex 창도 같은 원장에 기록·복구한다.)

> claude 를 `@resurrect-processes` 에 넣지 말 것. resurrect 는 커맨드라인을 그대로 재실행하는데,
> `claude` 나 `claude -c` 로 띄운 창은 **엉뚱한(혹은 빈) 대화**로 살아난다. 세션 ID 를 알고
> 복구하는 건 이 스킬 몫이고, 둘 다 켜면 창 하나에 claude 가 두 번 뜬다.

## 🚨 핵심 원칙 — 죽은 뒤에 추측하지 마라

**어느 창이 어느 대화였는지는 살아있을 때만 확실히 알 수 있다.** 죽은 뒤 `mtime` 순서로
고르면 같은 cwd 를 쓰는 창끼리 뒤바뀐다 — 실제로 그렇게 한 번 틀렸고(그 사고가 이 스킬을 만든 계기),
잘못 살아난 세션을 다시 닫고 올바른 것으로 교체해야 했다.

그래서 구조는 **원장(ledger) 기록 → 재생** 이다. 복구는 추론하지 않고 원장을 재생만 한다.

## 커맨드

```bash
S=~/.claude/skills/nydus-revive/scripts/nydus_sessions.py

python3 $S snapshot        # 살아있을 때 창→세션 원장 기록 (자동 배선 권장, 아래)
python3 $S status          # 원장 대비 현재 상태 — 어느 창이 죽었는지
python3 $S restore --dry-run   # 무엇을 어떻게 되살릴지만 출력
python3 $S restore         # 죽은 창만 되살림 (살아있는 창은 절대 안 건드림)
python3 $S restore --include-exited   # 크래시 전에 사용자가 닫은 창까지 되살림
python3 $S install-hook    # continuum 저장마다 snapshot 되도록 ~/.tmux.conf 에 배선
```

`--session <이름>` 으로 다른 tmux 세션도 대상 지정 가능(기본 `nydus`).
`--window N` 으로 한 창만 복구(이때는 exited 여부와 무관하게 복구). 원장 경로는 `NYDUS_LEDGER` 로 교체 가능(테스트용).

원장 항목의 `kind` 가 `claude`/`codex` 를 구분한다(옛 원장에 없으면 claude). `exited_at` 은
**tmux 서버는 그대로인데 프로세스만 사라진** 스냅샷에서 찍힌다 = 사용자가 직접 닫은 창. 그런 창은
`status` 에 "크래시 전 종료" 로 나오고 `restore` 가 기본으로 건너뛴다(2026-09-05 크래시 30분 전에
닫힌 창을 복구 대상으로 잡았던 오판 방지). 서버 `start_time` 이 마지막 원장보다 늦으면 크래시 후
첫 스냅샷이므로 exited_at 을 찍지 않는다.

원장: `~/.local/state/nydus-revive/ledger.json` (+ `history/` 최근 20개 보관)

## 절차

### 평상시 (1회 배선)
`install-hook` 을 돌린다. `@resurrect-hook-post-save-all` 에 snapshot 이 걸려
**continuum 이 저장할 때마다(기본 15분) 원장이 함께 갱신**된다. 즉 최악의 경우에도
15분 이내 상태로 복구된다.

### 죽고 난 뒤
1. `status` — 죽은 창 확인. 원장이 몇 분 전 것인지도 같이 나온다.
2. `restore --dry-run` — 창별로 어떤 커맨드가 나갈지 눈으로 확인.
3. `restore` — 실행. 창마다 1.5초 간격으로 띄운다(동시에 띄우면 첫 렌더가 엉킨다).
4. 각 창을 `capture-pane` 으로 확인 — **복원된 recap 이 죽기 전 그 창의 주제와 맞는지** 대조.
   틀렸으면 그 창에서 `/exit` 후 올바른 ID 로 다시 `--resume`.

## 세션 ID 를 알아내는 방법 (신뢰도 순)

### codex
1. **lsof** — codex 는 자기 rollout 파일(`~/.codex/sessions/YYYY/MM/DD/rollout-…-<uuid>.jsonl`)을
   **열어둔 채로** 돈다. `lsof -p <pid>` 의 그 경로가 지금 세션이다 — argv 보다 확실하다.
   (claude 는 파일을 열어두지 않아 이 방법이 안 통한다.)
2. **argv** — `codex … resume <uuid>`. `resume --last` 는 어느 세션인지 argv 로는 모른다.
3. **화면 대조** — 최근 rollout 60개 중 `session_meta.cwd` 가 창의 cwd 와 같은 것들과 대조.
   기준은 아래 claude 와 같다.

복구 커맨드는 전역 플래그(`--dangerously-bypass-approvals-and-sandbox`, `-m` …)를 보존하고
`resume <id>` 를 붙인다. 모델은 `~/.codex/config.toml` 기본값을 따르므로 보정하지 않는다.
`codex exec …` 처럼 resume 이 아닌 서브커맨드로 뜬 창은 대화가 아니라 되살리지 않는다.

### claude

1. **argv** — `--resume/-r <id>` 또는 `--session-id <id>` 가 커맨드라인에 있으면 **시작 시점의** 세션.
   한 번 이 스킬로 복구된 창은 이후 argv 에 ID 를 달고 있다(자기 식별).
   🚨 **단, claude 안에서 `/resume` 으로 갈아타면 argv 는 옛 ID 그대로다.** 2026-08-23 두 창이 그 상태였고
   원장이 옛 세션을 "확정"으로 기록해 복구가 틀렸다. 그래서 snapshot 은 argv 가 있어도 화면 지문(3)을
   대조해 화면이 다른 세션을 확실히 가리키면 화면을 우선한다(`화면 우선(argv … 불일치)` 로 표시).
   복구 후엔 반드시 `capture-pane` 으로 주제를 대조하고, 틀리면 그 cwd 프로젝트 세션 파일을
   **마지막 timestamp 순**으로 나열해 터진 시각 직전 것을 고른다(mtime 은 복구가 건드려 오염됨).
2. **cwd 에 세션이 1개뿐** — 모호성이 없으므로 확정.
3. **화면 대조** — 보이는 화면의 문장이 가장 많이 들어있는 세션 파일. 최고점이 차점과
   같거나 0이면 **기록하지 않는다**(틀린 기록보다 빈칸이 낫다).
   두 창이 같은 ID 를 주장하면 둘 다 버린다.

### 알아둘 함정 (전부 실제로 밟았다)
- 🚨 **`capture-pane` 에 `-S -N` 을 주지 마라.** Claude 는 alternate screen 에서 돈다.
  거기엔 히스토리가 없어서 `-S -400` 을 주면 tmux 가 **그 이전 셸의 옛 스크롤백**을 준다.
  지금 대화와 무관한 내용이라 지문이 통째로 오염된다. 보이는 화면만 잡아야 한다.
- 🚨 **`pgrep -P <pane_pid>` 로 claude 를 찾지 마라.** 창에 따라 재-부모화돼서 놓친다.
  `ps -t <pane_tty>` 로 tty 기준으로 찾아야 4창 전부 잡힌다. 같은 tty 에 MCP 헬퍼
  (`node .../launcher.mjs`)가 붙으니 실행파일명이 `claude` 인 것만 골라야 한다.
  codex 도 같은 tty 에 `codex-code-mode-host` 헬퍼가 붙으므로 실행파일명이 **정확히** `codex` 여야 한다.
- **원장이 없던 시절의 codex 창을 사후 대조할 때** — resurrect 의 `pane_contents.tar.gz`
  (`~/.local/share/tmux/resurrect/`, 마지막 저장 시점 화면)와 rollout 파일의 마지막 timestamp 를
  맞춰본다. 2026-09-06 에는 그렇게 창 3·4·5 를 rollout 3개와 1:1 로 확정했다.
- **화면(렌더된 마크다운) ≠ 파일(원문 JSON)** — `**굵게**` 는 화면에 별표가 없고, 줄바꿈·
  들여쓰기도 다르다. 양쪽에서 공백/강조기호/역슬래시를 걷어낸 뒤 대조해야 맞는다.
- **세션 저장 위치는 실행 당시 cwd 기준**이다. 세션 도중 워크트리로 이동하면 창의 cwd 와
  어긋날 수 있어, cwd 후보가 비면 전체 최근 세션으로 넓혀 대조한다.

## 안전 규칙

- **살아있는 claude/codex 는 절대 건드리지 않는다** — 죽은 창만 대상.
- 세션 ID 를 모르면 **추측해서 띄우지 않는다.** 실패로 보고하고 사람이 판단하게 둔다.
- `restore` 는 `send-keys` 로 셸에 커맨드를 넣는다. 대상 창이 맨 셸일 때만 실행된다.

## 한계 (복원되지 않는 것)

- **입력창에 타이핑만 하고 안 보낸 텍스트** — UI 상태라 세션에 저장되지 않는다.
- **effort 레벨**(`/effort xhigh` 등) — CLI 플래그가 없어 세션 UI 상태로만 존재한다.
- **claude/codex 가 아닌 프로세스**(`python -m nao.bot` 같은 상시 프로세스) — 기록/복구 대상이 아니다.
  그런 상시 프로세스는 launchd 가 감독하는 게 정석이다(m4-mini 의 nao 봇·fleta 는 2026-09-06 부터
  `~/naokr/launchd.sh` 의 LaunchAgent 로 돌고, nydus 창은 `tail -F` 뷰어일 뿐이다 — `tail` 은
  `@resurrect-processes` 에 있어 창째로 돌아온다).
- 모델은 argv 의 `--model`, 없으면 세션 파일에 기록된 마지막 모델로 복원한다(claude 만).
- codex 의 MCP OAuth(예: `codex mcp login verticalbar-next`)는 재개 후 다시 로그인해야 할 수 있다.
