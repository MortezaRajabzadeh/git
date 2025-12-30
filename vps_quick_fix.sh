#!/bin/bash
# Quick fix script for VPS Chrome issues

echo "🔧 VPS Quick Fix for Chrome/Selenium Issues"
echo "==========================================="

# 1. Install missing dependencies
echo "📦 Installing Chrome dependencies..."
apt-get update
apt-get install -y \
    xvfb \
    x11-utils \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils

# 2. Fix urllib3 version issue
echo "🔄 Fixing urllib3 compatibility..."
pip3 install --upgrade urllib3==1.26.15 requests

# 3. Kill any existing Chrome/Xvfb processes
echo "🧹 Cleaning up old processes..."
pkill -f chrome
pkill -f Xvfb
sleep 2

# 4. Start Xvfb
echo "🖥️  Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
sleep 3

# 5. Verify Xvfb is running
if pgrep -f "Xvfb :99" > /dev/null; then
    echo "✓ Xvfb is running"
else
    echo "❌ Failed to start Xvfb"
    exit 1
fi

# 6. Set environment variables
export DISPLAY=:99
export CHROME_BIN=/usr/bin/google-chrome
export CHROME_PATH=/usr/bin/google-chrome

# 7. Test Chrome
echo "🧪 Testing Chrome..."
google-chrome --version
if [ $? -eq 0 ]; then
    echo "✓ Chrome is installed"
else
    echo "❌ Chrome not found, installing..."
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    apt install -y ./google-chrome-stable_current_amd64.deb
    rm google-chrome-stable_current_amd64.deb
fi

# 8. Clean up old browser profiles
echo "🗑️  Cleaning old browser profiles..."
rm -rf browser_profiles/*/SingletonLock
rm -rf browser_profiles/*/SingletonSocket

echo ""
echo "✅ Setup complete! Now run:"
echo "   DISPLAY=:99 python3 main.py"
echo ""
echo "Or use the helper script:"
echo "   bash run_vps.sh"
