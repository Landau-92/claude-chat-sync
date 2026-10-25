#!/bin/zsh
# Builds build/Claude Chat Sync.app from source. Needs the Xcode Command Line Tools (swiftc).
set -euo pipefail
HERE=${0:A:h}
ROOT=${HERE:h}
NAME="Claude Chat Sync"
OUT="$ROOT/build"
APP="$OUT/$NAME.app"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -parse-as-library -O -target "$(uname -m)-apple-macos14.0" "$HERE/main.swift" \
  -o "$APP/Contents/MacOS/ClaudeChatSync"

# The command the app runs, bundled so the two always match
cp "$ROOT/bin/claude-chat" "$APP/Contents/Resources/claude-chat"
chmod +x "$APP/Contents/Resources/claude-chat"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>ClaudeChatSync</string>
  <key>CFBundleIdentifier</key><string>io.github.claude-chat-sync</string>
  <key>CFBundleName</key><string>Claude Chat Sync</string>
  <key>CFBundleDisplayName</key><string>Claude Chat Sync</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

# Icon: drawn with Pillow when available, otherwise the app keeps the generic icon
if python3 -c "import PIL" 2>/dev/null; then
  python3 "$HERE/make_icon.py" "$WORK/icon.png"
  mkdir -p "$WORK/AppIcon.iconset"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$WORK/icon.png" --out "$WORK/AppIcon.iconset/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$WORK/icon.png" --out "$WORK/AppIcon.iconset/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$WORK/AppIcon.iconset" -o "$APP/Contents/Resources/AppIcon.icns"
else
  echo "Pillow not installed (pip3 install --user pillow): building without the custom icon."
fi

# Ad-hoc signature: enough to run a locally built app
codesign --force --sign - "$APP"
echo "Built: $APP"
