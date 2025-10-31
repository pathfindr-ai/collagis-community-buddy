#!/bin/bash

# --- CONFIG ---
PLIST_PATH="$HOME/Library/LaunchAgents/com.collagis.autorun.plist"
APP_PATH="/Users/mini/Downloads/collagis/dist/AutomationAppV4"
WORK_DIR="/Users/mini/Downloads/collagis"
LOG_OUT="/tmp/collagis_autorun.log"
LOG_ERR="/tmp/collagis_autorun.err"

echo "🔧 Setting up Collagis autorun..."

# 1. Ensure directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# 2. Write plist file
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.collagis.autorun</string>

    <key>ProgramArguments</key>
    <array>
      <string>$APP_PATH</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$WORK_DIR</string>

    <key>StartInterval</key>
    <integer>300</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_OUT</string>

    <key>StandardErrorPath</key>
    <string>$LOG_ERR</string>
  </dict>
</plist>
EOF

echo "✅ Plist created at: $PLIST_PATH"

# 3. Reload and start the agent
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"
launchctl start com.collagis.autorun

# 4. Verify
echo "🔍 Checking status..."
launchctl list | grep collagis && echo "✅ Collagis autorun is active." || echo "❌ Collagis autorun not found."

# 5. Optional: show recent logs
echo
echo "📜 Error log:"
cat "$LOG_ERR" 2>/dev/null || echo "(no errors yet)"

