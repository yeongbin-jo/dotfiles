# ============================================================
#  ~/.zshrc  (공통 설정 — dotfiles 레포에서 관리)
#  민감/머신별 설정은 ~/.zshrc.local (커밋 안 함, 맨 끝에서 source)
# ============================================================

# ── oh-my-zsh ──
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="agnoster"
plugins=(git)

# Docker CLI 자동완성 fpath: oh-my-zsh 의 compinit 전에 추가 (중복 compinit 방지)
fpath=("$HOME/.docker/completions" $fpath)
source "$ZSH/oh-my-zsh.sh"

# ── 기본 환경 ──
export LANG=ko_KR.UTF-8
export EDITOR='vim'
export SHELL=/bin/zsh
export KEYTIMEOUT=1
export POETRY_VIRTUALENVS_IN_PROJECT=true

# 프롬프트: agnoster 앞에 날짜/시간 세그먼트 (반드시 oh-my-zsh source 뒤)
SEGMENT_SEPARATOR=$''
PROMPT='%{$fg[black]%}%{$bg[green]%} %D{%y/%m/%d} %D{%H:%M:%S} %{$fg[green]%}%{$bg[black]%}$SEGMENT_SEPARATOR'$PROMPT
DISABLE_UPDATE_PROMPT=true

# ── vi 모드 키바인딩 ──
set -o vi
bindkey -v
bindkey '\e[3~' delete-char
bindkey '^R' history-incremental-search-backward   # fzf 미설치 시 fallback
set -K

# ── brew ──
eval "$(/opt/homebrew/bin/brew shellenv)"

# ── PATH ──
export PATH="$PATH:$HOME/.local/bin"
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"                       # psql
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/36.0.0"
export PATH="$HOME/.antigravity/antigravity/bin:$PATH"
export PATH="$HOME/.opencode/bin:$PATH"

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
case ":$PATH:" in *":$PNPM_HOME:"*) ;; *) export PATH="$PNPM_HOME:$PATH" ;; esac

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# cargo
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# ── 런타임 매니저 (lazy = 셸 시작 빠르게) ──
# nvm: nvm/node/npm/npx/corepack 첫 호출 시에만 로드
export NVM_DIR="$HOME/.nvm"
_nvm_lazy() { unset -f nvm node npm npx corepack 2>/dev/null; [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"; [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"; }
nvm()      { _nvm_lazy; nvm "$@"; }
node()     { _nvm_lazy; node "$@"; }
npm()      { _nvm_lazy; npm "$@"; }
npx()      { _nvm_lazy; npx "$@"; }
corepack() { _nvm_lazy; corepack "$@"; }

# pyenv: shims 즉시 PATH(= python/pip/poetry 동작), 무거운 init은 첫 pyenv 호출 시
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
pyenv() { unset -f pyenv; eval "$(command pyenv init - zsh)"; pyenv "$@"; }

# direnv
eval "$(direnv hook zsh)"

# google-cloud-sdk
[ -f "$HOME/Downloads/google-cloud-sdk/path.zsh.inc" ]       && . "$HOME/Downloads/google-cloud-sdk/path.zsh.inc"
[ -f "$HOME/Downloads/google-cloud-sdk/completion.zsh.inc" ] && . "$HOME/Downloads/google-cloud-sdk/completion.zsh.inc"

# ── 별칭 ──
alias vi="vim"
alias dps='docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"'
alias claude-yolo='claude --dangerously-skip-permissions'
alias codex-yolo='codex --dangerously-bypass-approvals-and-sandbox'
alias clean_cache='rm -rf ~/Library/Developer/Xcode/DerivedData/* ~/Library/Developer/Xcode/iOS\ DeviceSupport/* ~/Library/Caches/*'

# ── nydus: Tailscale 머신의 tmux 세션 attach-or-create (ssh+tmux 터널) ──
#   nydus / nydus <host>  →  세션 안에서 claude, 빠져나오기 Ctrl-b d
nydus() { [ -z "$1" ] && tmux new -A -s nydus || ssh -t "$1" 'tmux new -A -s nydus'; }

# ── 머신별/민감 설정 (장비 alias 등, 커밋 안 함) ──
[ -f "$HOME/.zshrc.local" ] && source "$HOME/.zshrc.local"

# ── 모던 CLI 도구 (설치돼 있을 때만 로드 → fresh 머신서도 에러 없음) ──
command -v fzf    >/dev/null && source <(fzf --zsh)        # Ctrl-R 히스토리 / Ctrl-T 파일 / Alt-C 디렉터리
command -v zoxide >/dev/null && eval "$(zoxide init zsh)"   # z <dir> 스마트 점프
if command -v eza >/dev/null; then
  alias ls='eza --group-directories-first'
  alias ll='eza -lah --git --group-directories-first'
  alias la='eza -lah --group-directories-first'
  alias lt='eza --tree --level=2'
fi
command -v bat >/dev/null && alias cat='bat --paging=never'
[ -r /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ] && source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
# zsh-syntax-highlighting 은 반드시 맨 마지막 source
[ -r /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ] && source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# 커서는 Ghostty 설정으로 처리 (shell-integration-features=no-cursor + cursor-style=block)
