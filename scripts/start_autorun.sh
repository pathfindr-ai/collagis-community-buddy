#!/bin/bash
launchctl load ~/Library/LaunchAgents/com.collagis.autorun.plist
launchctl start com.collagis.autorun
echo "🟢 Collagis autorun started."
