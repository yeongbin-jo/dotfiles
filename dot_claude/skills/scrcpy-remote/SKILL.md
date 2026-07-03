---
name: scrcpy-remote
description: Mirror/control an Android device that is USB-attached to one Mac on a DIFFERENT Mac's screen via scrcpy over Tailscale. Use when the user asks to open scrcpy / mirror / control a device on a machine that is not the one it is plugged into (e.g. device on one laptop, view+control on another). Runs the bundled scrcpy-remote.sh from the Mac the device is plugged into.
---

# scrcpy-remote — 원격 Mac 에서 USB 기기 미러링

## When to use

- 안드로이드 기기가 **한 Mac 에 USB** 로 붙어 있고, 사용자는 **다른 Mac 의 화면**에서 그 기기를 보고/조작하고 싶다.
- 사용자가 자리를 옮겨 다른 노트북 앞에 있을 때(“scrcpy 띄워줘”, “폰 화면 저쪽 노트북에 띄워”).
- 기기가 붙은 그 Mac 에서 로컬로 `scrcpy` 한 줄이면 되는 **일반 케이스는 이 스킬 불필요** — 이건 크로스머신 전용.

## 사용법 (기기가 붙은 Mac 에서 실행)

```bash
~/.claude/skills/scrcpy-remote/scrcpy-remote.sh [VIEW_HOST] [SERIAL]
# 기본값: VIEW_HOST=m4-air, SERIAL=이 Mac 의 첫 device
# 예) scrcpy-remote.sh m4-air              # 시리얼 자동감지
# 종료: scrcpy-remote.sh --stop m4-air
```

스크립트가 하는 일: 로컬 adb 서버(IPv4) 보장 → view host 로 SSH 리버스터널(keepalive, 데몬) → view host 에서 scrcpy 실행. 터널은 데몬화(`-fN`)라 이 세션이 끝나도 유지된다.

## 전제

- 두 Mac 모두 **Tailscale 연결** + 서로 `ssh <host>` alias 로 접속 가능(키 기반).
- **view host 는 GUI 콘솔에 해당 유저로 로그인** 돼 있어야 창이 물리 화면에 뜬다(헤드리스면 안 뜸).
- 양쪽에 `scrcpy`/`adb`(brew, `/opt/homebrew/bin`). view host 최초 1회 macOS **“로컬 네트워크” 권한 프롬프트 승인** 필요(그 후엔 안 물음).
- m4-air 처럼 IP 가 stale 할 수 있으면 `tailscale status` 로 실 IP 확인.

## 실측 함정 (스크립트가 이미 처리 — 손으로 재현 시 주의)

1. **adb 서버는 기본 127.0.0.1:5037 (IPv4)**. `adb -a` 는 IPv6-only 바인딩이라 tailscale IPv4 접속이 timeout. 그래서 tailscale 직접이 아니라 **SSH 리버스터널로 127.0.0.1 통일**.
2. **scrcpy 비디오 forward 포트는 항상 기본 27183** (`--tunnel-port` 를 줘도 forward 는 27183 에 생김). `-R` 터널도 27183 을 그대로 실어야 함 — 안 맞추면 `ERROR: Server connection failed` 로 즉사.
3. 기기가 view host 로 되돌아 연결 못 하므로 **`--force-adb-forward` 필수**(기본 `adb reverse` 는 이 토폴로지서 실패).
4. view host 의 non-interactive SSH PATH 엔 brew 가 없어 scrcpy 가 adb 를 못 찾음 → **`ADB` 환경변수에 전체경로**.
5. **SSH keepalive**(`ServerAliveInterval`) 없으면 idle 로 터널이 끊겨 scrcpy 가 죽는다.

## 디버그

- view host: `tail -f /tmp/scrcpy_remote.log`. `Renderer: metal` + `Texture: WxH` 나오면 렌더 성공.
- `Server connection failed` = 포트 불일치(함정 #2) 또는 터널 미기동.
- 창이 안 뜨는데 프로세스는 alive = view host GUI 미로그인 또는 로컬네트워크 권한 미승인.
- 터널 생존: 기기 붙은 Mac 에서 `pgrep -fl "ssh.*-R 5039"`.
