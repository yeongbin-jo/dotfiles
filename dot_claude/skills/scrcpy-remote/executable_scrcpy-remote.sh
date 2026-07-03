#!/usr/bin/env bash
# scrcpy-remote — USB 로 THIS Mac 에 붙은 안드로이드 기기를 원격 Mac 의 화면에 scrcpy 로 띄운다.
# (예: 폰은 m2-air USB, 화면/조작은 m4-air). Tailscale + SSH 리버스터널 사용.
#
# 사용: scrcpy-remote.sh [VIEW_HOST] [SERIAL]
#   VIEW_HOST  scrcpy 를 띄울 원격 ssh 호스트 (기본: m4-air). GUI 콘솔에 로그인돼 있어야 창이 뜸.
#   SERIAL     adb 시리얼 (기본: 이 Mac 의 첫 번째 device)
#   teardown:  scrcpy-remote.sh --stop [VIEW_HOST]
#
# 왜 이렇게까지 해야 하나 (전부 실측 함정):
#   1) adb 서버는 반드시 기본 127.0.0.1:5037 (IPv4). `adb -a` 는 IPv6-only 로 바인딩돼
#      tailscale IPv4 접속이 timeout 난다. → SSH 리버스터널로 127.0.0.1 통일.
#   2) scrcpy 는 --tunnel-port 를 줘도 비디오 forward 를 **기본 27183** 에 만든다.
#      따라서 -R 터널도 27183 을 그대로 실어야 한다(다른 포트 주면 "Server connection failed").
#   3) 기기가 원격(view) 호스트로 되돌아 연결 못 하므로 --force-adb-forward 필수.
#   4) 원격 ssh 의 PATH 에 brew 가 없어 scrcpy 가 adb 를 못 찾음 → ADB 환경변수 전체경로.
#   5) SSH keepalive(ServerAliveInterval) 없으면 idle 로 터널이 끊겨 scrcpy 가 죽는다.
#   6) 최초 1회 원격 Mac 에서 macOS "로컬 네트워크" 권한 프롬프트 → 승인(그 뒤론 안 물음).
set -euo pipefail

VIEW_HOST="${2:-m4-air}"
[ "${1:-}" = "--stop" ] && {
  ssh "$VIEW_HOST" "pkill -f 'scrcpy .*--force-adb-forward'" 2>/dev/null || true
  pkill -f "ssh.* -R 5039:127.0.0.1:5037 .* ${VIEW_HOST}" 2>/dev/null || true
  echo "stopped scrcpy + tunnel on ${VIEW_HOST}"; exit 0; }

VIEW_HOST="${1:-m4-air}"
SERIAL="${2:-$(adb devices | awk 'NR>1 && $2=="device"{print $1; exit}')}"
[ -z "${SERIAL:-}" ] && { echo "no adb device on this Mac"; exit 1; }

ADB_PORT=5039        # 원격측 adb 서버 프록시 포트
VID_PORT=27183       # scrcpy 기본 비디오 forward 포트 — 양끝 동일해야 함 (함정 #2)
R_ADB="/opt/homebrew/bin/adb"
R_SCRCPY="/opt/homebrew/bin/scrcpy"

# 1. 로컬 adb 서버 (127.0.0.1:5037 IPv4). `-a` 금지 (함정 #1)
adb start-server >/dev/null 2>&1 || true

# 2. 이전 잔여 정리 (이 view host 대상만)
pkill -f "ssh.* -R ${ADB_PORT}:127.0.0.1:5037 .* ${VIEW_HOST}" 2>/dev/null || true
ssh "$VIEW_HOST" "pkill -f 'scrcpy .*${SERIAL}'" 2>/dev/null || true
sleep 1

# 3. SSH 리버스터널 (keepalive, 데몬화). view:5039→로컬 adb, view:27183→로컬 27183
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
    -o TCPKeepAlive=yes -fN \
    -R ${ADB_PORT}:127.0.0.1:5037 -R ${VID_PORT}:127.0.0.1:${VID_PORT} "$VIEW_HOST"

# 4. 원격에서 scrcpy 실행 (GUI 는 view host 콘솔 세션 화면에 뜸)
ssh "$VIEW_HOST" "export ADB='${R_ADB}' ADB_SERVER_SOCKET=tcp:127.0.0.1:${ADB_PORT}; \
  nohup '${R_SCRCPY}' -s ${SERIAL} --force-adb-forward --stay-awake \
  --window-title='${SERIAL} (remote USB)' >/tmp/scrcpy_remote.log 2>&1 & echo scrcpy-pid \$!"

echo "▶ ${VIEW_HOST} 화면에 ${SERIAL} scrcpy 실행됨. 로그: ${VIEW_HOST}:/tmp/scrcpy_remote.log"
echo "  안 뜨면 view host 콘솔 로그인 여부 / 최초 로컬네트워크 권한 프롬프트 확인."
echo "  종료: scrcpy-remote.sh --stop ${VIEW_HOST}"
