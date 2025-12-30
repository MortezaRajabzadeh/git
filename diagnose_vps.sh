#!/bin/bash
# VPS Diagnostic Script

echo "🔍 VPS Environment Diagnostic"
echo "=============================="
echo ""

# Check OS
echo "📋 Operating System:"
cat /etc/os-release | grep PRETTY_NAME
echo ""

# Check Python
echo "🐍 Python Version:"
python3 --version
echo ""

# Check Chrome
echo "🌐 Chrome:"
if command -v google-chrome &> /dev/null; then
    google-chrome --version
    echo "✓ Chrome installed"
else
    echo "❌ Chrome NOT installed"
fi
echo ""

# Check Xvfb
echo "🖥️  Xvfb:"
if command -v Xvfb &> /dev/null; then
    echo "✓ Xvfb installed"
    if pgrep -f "Xvfb :99" > /dev/null; then
        echo "✓ Xvfb is running on :99"
    else
        echo "⚠️  Xvfb not running"
    fi
else
    echo "❌ Xvfb NOT installed"
fi
echo ""

# Check DISPLAY
echo "📺 Display Environment:"
echo "DISPLAY=$DISPLAY"
if [ -z "$DISPLAY" ]; then
    echo "⚠️  DISPLAY not set"
else
    echo "✓ DISPLAY is set"
fi
echo ""

# Check Python packages
echo "📦 Python Packages:"
pip3 list | grep -E "selenium|undetected-chromedriver|pynput|urllib3|requests"
echo ""

# Check running processes
echo "🔄 Running Processes:"
echo "Chrome processes: $(pgrep -f chrome | wc -l)"
echo "Xvfb processes: $(pgrep -f Xvfb | wc -l)"
echo ""

# Check browser profiles
echo "📁 Browser Profiles:"
if [ -d "browser_profiles" ]; then
    echo "Profile directory exists"
    echo "Number of profiles: $(ls -1 browser_profiles 2>/dev/null | wc -l)"
    
    # Check for lock files
    locks=$(find browser_profiles -name "SingletonLock" 2>/dev/null | wc -l)
    if [ $locks -gt 0 ]; then
        echo "⚠️  Found $locks lock files (may cause issues)"
    fi
else
    echo "⚠️  browser_profiles directory not found"
fi
echo ""

# Check network
echo "🌍 Network Connectivity:"
if ping -c 1 github.com &> /dev/null; then
    echo "✓ Can reach github.com"
else
    echo "❌ Cannot reach github.com"
fi
echo ""

# Check memory
echo "💾 Memory Usage:"
free -h
echo ""

# Check disk space
echo "💿 Disk Space:"
df -h / | tail -1
echo ""

# Recommendations
echo "📝 Recommendations:"
echo "================================"

if ! command -v Xvfb &> /dev/null; then
    echo "❌ Install Xvfb: apt install -y xvfb"
fi

if ! command -v google-chrome &> /dev/null; then
    echo "❌ Install Chrome: bash vps_quick_fix.sh"
fi

if [ -z "$DISPLAY" ]; then
    echo "⚠️  Set DISPLAY: export DISPLAY=:99"
fi

if ! pgrep -f "Xvfb :99" > /dev/null; then
    echo "⚠️  Start Xvfb: Xvfb :99 -screen 0 1920x1080x24 &"
fi

locks=$(find browser_profiles -name "SingletonLock" 2>/dev/null | wc -l)
if [ $locks -gt 0 ]; then
    echo "⚠️  Clean locks: rm -rf browser_profiles/*/SingletonLock"
fi

echo ""
echo "✅ Run: bash vps_quick_fix.sh to fix common issues"
