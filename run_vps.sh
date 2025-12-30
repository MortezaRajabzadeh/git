#!/bin/bash
# Quick run script for VPS with Xvfb support

echo "🚀 Starting GitHub Account Creator on VPS..."

# Check if Xvfb is installed
if ! command -v Xvfb &> /dev/null; then
    echo "❌ Xvfb not found. Run: bash vps_quick_fix.sh"
    exit 1
fi

# Kill any existing Chrome processes
pkill -f chrome 2>/dev/null

# Check if Xvfb is already running on :99
if pgrep -f "Xvfb :99" > /dev/null; then
    echo "✓ Xvfb already running on :99"
else
    echo "🖥️  Starting virtual display (Xvfb)..."
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
    sleep 3
    echo "✓ Virtual display started"
fi

# Set environment variables
export DISPLAY=:99
export CHROME_BIN=/usr/bin/google-chrome
export CHROME_PATH=/usr/bin/google-chrome

# Clean up old browser locks
rm -rf browser_profiles/*/SingletonLock 2>/dev/null
rm -rf browser_profiles/*/SingletonSocket 2>/dev/null

# Run the main script
echo "▶️  Running main.py..."
python3 main.py

# Cleanup on exit
trap "echo '🛑 Stopping...'; pkill -f chrome; exit" INT TERM
