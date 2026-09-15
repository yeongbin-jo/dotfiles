---
name: dotfiles-sync
description: Update and apply this machine's dotfiles, which are split across two chezmoi sources — a public repo and a private overlay. Use when pulling the latest dotfiles, when changing anything under $HOME that chezmoi manages (~/.zshrc, ~/.ssh/config, ~/.claude, ~/.codex, LaunchAgents, Brewfile), or when a change made in $HOME was silently reverted. Also use before editing any file that might be chezmoi-managed, to find its source path first.
---

# dotfiles-sync

## 왜 이 스킬이 필요한가

이 머신의 dotfiles 는 **chezmoi 소스가 두 개**다.

| | 경로 | 리모트 | 역할 |
|---|---|---|---|
| public | `~/.local/share/chezmoi` | `yeongbin-jo/dotfiles` (`master`) | 3대 Mac 공통. 공개돼도 되는 것만 |
| private overlay | `~/.local/share/chezmoi-private` | `yeongbin-jo/dotfiles-private` (`main`) | IP·호스트·터널·계정 등 비공개. **public 을 덮어쓴다** |

그래서 두 가지가 자주 틀린다.

1. **`$HOME` 의 파일을 직접 고치면 다음 apply 에 되돌아간다.** 관리 대상 파일은 소스에서 고쳐야 한다.
2. **한쪽만 apply 하면 역할이 어긋난다.** private 가 public 을 덮으므로 `public apply → private apply` 순서를 지켜야 한다.

`~/.local/bin/dotfiles-sync` 가 그 순서를 담고 있다. zsh 의 `dotup` 은 이 스크립트의 래퍼다.

## 1. 그냥 최신화만 할 때

```sh
dotfiles-sync
```

이게 하는 일: public `chezmoi update`(pull+apply) → private `git pull --ff-only` → `chezmoi -S <private> apply`.
`--dry-run`, `-v` 같은 인자는 그대로 두 apply 에 전달된다. 먼저 보고 싶으면:

```sh
dotfiles-sync --dry-run -v
```

## 2. 파일을 고칠 때 (중요)

**절대 `$HOME` 의 대상 파일을 직접 편집하지 않는다.** 순서는 항상 이렇다.

```sh
# ① 이 파일이 관리 대상인지, 소스가 어디인지 확인한다
chezmoi source-path ~/.zshrc                      # public 소스
chezmoi -S ~/.local/share/chezmoi-private source-path ~/.ssh/config   # private 소스
```

`source-path` 가 에러를 내면 그 소스가 관리하지 않는 파일이다. 두 소스 모두에서 에러면 chezmoi 관리 대상이 아니므로 직접 편집해도 된다.

```sh
# ② 소스에서 고친다
$EDITOR "$(chezmoi source-path ~/.zshrc)"

# ③ 적용 전에 무엇이 바뀌는지 본다
chezmoi diff                                       # public
chezmoi -S ~/.local/share/chezmoi-private diff     # private

# ④ 커밋(한글 메시지)하고 push 한 뒤 apply 한다
git -C ~/.local/share/chezmoi commit -am "zsh: …"        && git -C ~/.local/share/chezmoi push
git -C ~/.local/share/chezmoi-private commit -am "…"     && git -C ~/.local/share/chezmoi-private push
dotfiles-sync
```

커밋·push 는 사용자가 명시적으로 요청했을 때만 한다. 요청이 없으면 소스 편집과 `diff` 까지만 하고 보고한다.

## 3. public / private 중 어디에 넣을지

private 에 넣어야 하는 것:

- tailnet IP, 호스트명, 공인 IP, 포트 포워드 목록 (`.chezmoidata.yaml` 의 `personal_hosts`, `tunnels.forwards`)
- `~/.ssh/config`, LaunchAgent 중 위 정보를 담은 것
- 계정·이메일·토큰 경로가 드러나는 설정

public 에 넣어도 되는 것: 셸 함수·alias·플러그인, Brewfile, 에디터 설정, 스킬 문서, 신원과 무관한 스크립트.

**판단이 애매하면 private 에 넣는다.** public 레포에 한 번 올라간 값은 히스토리에 남는다.

`~/.claude/CLAUDE.md` 의 네트워크 토폴로지 문장은 private 의 `dot_claude/CLAUDE.md.tmpl` 이 정본이고, 데이터는 private 의 `.chezmoidata.yaml` 이다. 그 파일을 `$HOME` 에서 직접 고치지 않는다.

## 4. 기계가 늘거나 값이 바뀔 때

개인망 노드를 추가하면 데이터만 고치고 재적용한다.

```sh
$EDITOR ~/.local/share/chezmoi-private/.chezmoidata.yaml   # personal_hosts / tunnels.forwards
dotfiles-sync
```

호스트 목록을 바꿨으면 `/etc/hosts` 와 투명 프록시도 다시 깔아야 한다. 설치 명령은
`~/.claude/CLAUDE.md`(private 정본) 의 네트워크 절에 적혀 있다.

LaunchAgent 를 바꿨으면 apply 만으로는 안 붙는다. 다시 읽혀야 한다.

```sh
launchctl list | grep <라벨>                     # 라벨 확인
launchctl kickstart -k "gui/$UID/<라벨>"
```

라벨과 터널 구성은 public 에 적지 않는다. `CLAUDE.md` 의 상시 터널 표를 본다.

## 5. 확인

작업이 끝나면 아래가 모두 조용해야 한다.

```sh
chezmoi status                                       # 빈 출력 = public 적용 완료
chezmoi -S ~/.local/share/chezmoi-private status     # 빈 출력 = private 적용 완료
git -C ~/.local/share/chezmoi status --short --branch
git -C ~/.local/share/chezmoi-private status --short --branch
```

`ahead` 가 남아 있으면 push 하지 않은 커밋이 있다는 뜻이다. 다른 머신에서 `dotfiles-sync` 를 돌려도 그 변경은 오지 않는다.

## 하지 말 것

- `$HOME` 의 관리 대상 파일 직접 편집 — 다음 apply 에 사라진다.
- public 만 apply, 또는 private 를 먼저 apply — 덮어쓰기 순서가 깨진다.
- private 의 값(IP·호스트·계정)을 public 레포에 넣기.
- `git push --force`, `reset --hard` 로 dotfiles 히스토리 정리 — 3대 머신이 같은 히스토리를 본다.
