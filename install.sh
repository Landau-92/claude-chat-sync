#!/bin/zsh
# Builds Claude Chat Sync and installs it:
#   ~/Applications/Claude Chat Sync.app   the app
#   ~/.local/bin/claude-chat              the command line tool (a link into this checkout)
# An existing app is moved aside as "Claude Chat Sync.app.old", never deleted.
set -euo pipefail
ROOT=${0:A:h}

command -v swiftc >/dev/null || { echo "swiftc not found: install the Xcode Command Line Tools (xcode-select --install)"; exit 1; }
[[ -x /usr/bin/python3 ]] || { echo "/usr/bin/python3 not found: install the Xcode Command Line Tools"; exit 1; }

zsh "$ROOT/app/build.sh"

DEST="$HOME/Applications/Claude Chat Sync.app"
mkdir -p "$HOME/Applications"
if [[ -e "$DEST" ]]; then
  rm -rf "$DEST.old"
  mv "$DEST" "$DEST.old"
fi
cp -R "$ROOT/build/Claude Chat Sync.app" "$DEST"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$DEST" >/dev/null 2>&1 || true

mkdir -p "$HOME/.local/bin"
ln -sf "$ROOT/bin/claude-chat" "$HOME/.local/bin/claude-chat"

echo
echo "Installed:"
echo "  $DEST"
echo "  ~/.local/bin/claude-chat -> $ROOT/bin/claude-chat"
echo
echo "Open it with:  open \"$DEST\""
