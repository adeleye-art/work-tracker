#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PYTHON="$(which python3)"

echo "=== Work Tracker — Install ==="
echo "Script dir : $SCRIPT_DIR"
echo "Python     : $PYTHON"
echo ""

# 1. Install dependencies
echo "[1/4] Installing Python dependencies..."
python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet

# 2. Create reports folder
echo "[2/4] Creating ~/Documents/WorkReports/..."
mkdir -p "$HOME/Documents/WorkReports"

# 3. Write launchd plist — Logger (starts at login, restarts if it crashes)
echo "[3/4] Writing LaunchAgent plists..."
mkdir -p "$LAUNCH_AGENTS"

cat > "$LAUNCH_AGENTS/com.worktracker.logger.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.worktracker.logger</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/logger.py</string>
    </array>

    <!-- Start immediately when loaded and keep alive if it exits -->
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logger.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logger.err</string>
</dict>
</plist>
PLIST

# 4. Write launchd plist — Reporter (runs at 18:00 Mon–Fri)
cat > "$LAUNCH_AGENTS/com.worktracker.reporter.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.worktracker.reporter</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/reporter.py</string>
    </array>

    <!-- Fire at 18:00 on Mon(1)–Fri(5) -->
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
    </array>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/reporter.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/reporter.err</string>
</dict>
</plist>
PLIST

# 5. Load both agents (unload first to handle re-installs cleanly)
echo "[4/4] Loading LaunchAgents..."
launchctl unload "$LAUNCH_AGENTS/com.worktracker.logger.plist"   2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.worktracker.reporter.plist" 2>/dev/null || true

launchctl load "$LAUNCH_AGENTS/com.worktracker.logger.plist"
launchctl load "$LAUNCH_AGENTS/com.worktracker.reporter.plist"

echo ""
echo "Done!"
echo ""
echo "  Logger  : running now, restarts automatically at login"
echo "  Reporter: fires every weekday at 18:00"
echo "  Reports : ~/Documents/WorkReports/YYYY-MM-DD.xlsx"
echo ""
echo "  To check status : launchctl list | grep worktracker"
echo "  To run report now: python3 $SCRIPT_DIR/reporter.py"
echo "  Logger logs      : $SCRIPT_DIR/logger.log"
