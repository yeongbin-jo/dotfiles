# Brewfile — CLI tooling these dotfiles expect on a fresh macOS box.
# Run manually:  brew bundle --file=~/.local/share/chezmoi/Brewfile
# chezmoi does NOT run this automatically — it never touches brew on existing machines.

brew "chezmoi"
brew "age"
brew "git-delta"               # .gitconfig pager / diffFilter (lookPath-guarded)
brew "fzf"                     # Ctrl-R history / Ctrl-T files
brew "zoxide"                  # z smart-jump
brew "eza"                     # ls replacement
brew "bat"                     # cat replacement
brew "direnv"
brew "sshuttle"                # workstation: transparent proxy into the personal tailnet (installer lives in the private overlay)
brew "libpq"                   # psql client
brew "zsh-autosuggestions"
brew "zsh-syntax-highlighting"

# GUI utilities
cask "karabiner-elements"
cask "obsidian"
cask "ghostty"                 # terminal emulator (config: dot_config/ghostty/config)

# Fonts (Ghostty: DejaVu Sans Mono for Powerline primary + D2Coding Korean/glyph fallback)
cask "font-dejavu-sans-mono-for-powerline"
cask "font-d2coding"

# Not brew-managed (install separately):
#   oh-my-zsh   sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
#   nvm         https://github.com/nvm-sh/nvm
#   pyenv       brew install pyenv   (or pyenv-installer)
#   uv          https://docs.astral.sh/uv
#   rustup      https://rustup.rs
