defaults write -g com.apple.mouse.scaling 5
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-time-modifier -float 0
defaults write com.apple.dock autohide-delay -float 0
defaults write com.microsoft.VSCode ApplePressAndHoldEnabled -bool false
defaults write -g InitialKeyRepeat -int 10
defaults write -g KeyRepeat -int 1
killall Dock

export PLUGIN_PATH=${HOME}/.zsh-plugins
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
echo "source ~/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh" >> ${ZDOTDIR:-$HOME}/.zshrc
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
echo "source ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" >> ${ZDOTDIR:-$HOME}/.zshrc
git clone git://github.com/wting/autojump.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/autojump
cd ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/autojump
./install.sh
