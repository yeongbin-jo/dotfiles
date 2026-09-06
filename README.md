# dotfiles

[chezmoi](https://chezmoi.io)-managed dotfiles for my Apple-Silicon Macs.
One source for personal Macs. Per-machine differences are handled with Go templates,
secrets with [age](https://age-encryption.org) encryption.

## What's here

| source | target | notes |
|---|---|---|
| `dot_zshrc.tmpl` | `~/.zshrc` | oh-my-zsh (agnoster), vi-mode, lazy `nvm`/`pyenv`, modern CLI (fzf/zoxide/eza/bat) |
| `encrypted_dot_zshrc.local.tmpl` | `~/.zshrc.local` | machine/secret shell config — **age-encrypted** |
| `dot_gitconfig.tmpl` | `~/.gitconfig` | delta pager, guarded by `lookPath` |
| `dot_config/ghostty/config` | `~/.config/ghostty/config` | Ghostty terminal |
| `dot_config/private_karabiner` | `~/.config/karabiner` | Karabiner profile and complex modifications |
| `dot_local/bin` | `~/.local/bin` | operational helpers (`dotfiles-doctor`, `dotfiles-sync`, `remote-work-status`, `lock-screen`, `obsidian-vault`) |
| `dot_tmux.conf` · `dot_vimrc` · `dot_screenrc` | `~/.tmux.conf` … | editor and terminal session config |

`iterm2.json` and `macos.sh` are kept for reference and **not** deployed (`.chezmoiignore`d).

## Templating highlights

- Per-machine branches via a `machine` data var.
- Runtime managers load only when present (`stat ~/.nvm`, `stat ~/.pyenv`) — fresh
  machines never error on a missing tool.
- Tool-specific config guarded by `lookPath` (e.g. git's `delta`).
- Secrets live in an age-encrypted file; the private key is **not** in this repo.

## Fresh Machine

```sh
brew install chezmoi age
# restore the age key to ~/.config/chezmoi/key.txt (from your password manager)
chezmoi init --apply yeongbin-jo
git clone git@github.com:yeongbin-jo/dotfiles-private.git ~/.local/share/chezmoi-private   # private overlay
dotfiles-sync
brew bundle --file=~/.local/share/chezmoi/Brewfile
dotfiles-doctor
```

> chezmoi never runs `brew` on its own — package installs are always an explicit step.

## Public vs. private overlay

This public repo holds only generic, machine-agnostic config. Everything that
describes *my* machines — hostnames, IPs, tailnets, SSH config, tunnels,
company/project-specific skills — lives in a separate **private overlay** repo
applied on top (`chezmoi -S ~/.local/share/chezmoi-private apply`). Use
`dotfiles-sync` to update and apply both in the right order; a target path is
owned by exactly one of the two repos.

A pre-commit hook (`.githooks/pre-commit`, wired by chezmoi via
`core.hooksPath`) blocks commits to this repo that contain IPs, tailnet DNS
names (Tailscale MagicDNS), key/token signatures, or any pattern listed in
`~/.config/dotfiles/public-denylist` (deployed by the private overlay).

## Manual Gates

Some setup cannot be safely automated from a public dotfiles repo:

- Restore the age key from the password manager before applying encrypted files.
- Sign in to Tailscale from the GUI and choose the correct tailnet.
- Grant Karabiner-Elements the macOS permissions it requests.
- Configure SSH key-only login with administrator privileges.
- Decide whether Apple Watch auto-unlock should stay enabled on that machine.

Run `dotfiles-doctor` after each step. It reports local state without embedding
hostnames, tailnet names, keys, or account-specific secrets in this repository.

## Remote Work Mode

Use `remote-work-status` to verify that SSH, Tailscale, screen-lock policy, and
the keep-awake LaunchAgent are ready. Use `lock-screen` to lock the GUI session
immediately while keeping the machine available for SSH/tmux work.

## Obsidian Vault

The Obsidian vault is managed as a private Git repository, not in this public
dotfiles repository. The helper reads its path and remote from
`~/.config/obsidian-agent/config`, which is age-encrypted in chezmoi.

```sh
obsidian-vault init
obsidian-vault status
obsidian-vault sync
```

Agents should edit notes inside `$(obsidian-vault path)` and use
`obsidian-vault sync` after intentional changes. GUI-only Obsidian account and
plugin permissions are still manual.
