# dotfiles

[chezmoi](https://chezmoi.io)-managed dotfiles for my Apple-Silicon Macs.
One source, three machines — per-machine differences handled with Go templates,
secrets with [age](https://age-encryption.org) encryption.

## What's here

| source | target | notes |
|---|---|---|
| `dot_zshrc.tmpl` | `~/.zshrc` | oh-my-zsh (agnoster), vi-mode, lazy `nvm`/`pyenv`, modern CLI (fzf/zoxide/eza/bat) |
| `encrypted_dot_zshrc.local.tmpl` | `~/.zshrc.local` | machine/secret shell config — **age-encrypted** |
| `dot_gitconfig.tmpl` | `~/.gitconfig` | delta pager, guarded by `lookPath` |
| `dot_config/ghostty/config` | `~/.config/ghostty/config` | Ghostty terminal |
| `dot_tmux.conf` · `dot_vimrc` · `dot_screenrc` | `~/.tmux.conf` … | |

`iterm2.json` and `macos.sh` are kept for reference and **not** deployed (`.chezmoiignore`d).

## Templating highlights

- Per-machine branches via a `machine` data var (`m4-air` / `m2-air` / `m4-pro`).
- Runtime managers load only when present (`stat ~/.nvm`, `stat ~/.pyenv`) — fresh
  machines never error on a missing tool.
- Tool-specific config guarded by `lookPath` (e.g. git's `delta`).
- Secrets live in an age-encrypted file; the private key is **not** in this repo.

## Fresh machine

```sh
brew install chezmoi age
# restore the age key to ~/.config/chezmoi/key.txt (from your password manager)
chezmoi init --apply yeongbin-jo
brew bundle --file=~/.local/share/chezmoi/Brewfile   # optional CLI tools
```

> chezmoi never runs `brew` on its own — package installs are always an explicit step.
