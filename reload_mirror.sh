#!/bin/bash

# Reload Driver with Screen Mirroring
# Usage: sudo ./reload_mirror.sh

echo "=== RELOAD DRIVER WITH MIRRORING ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔄 Checking current driver status..."
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver is currently loaded"
else
    echo "❌ Driver is not loaded"
fi

echo ""
echo "🔄 Unloading current driver..."
rmmod gm12u320 2>/dev/null || echo "Driver not loaded or already unloaded"

echo "⏳ Waiting 3 seconds..."
sleep 3

echo "🔄 Loading driver with screen_mirror=true..."
insmod gm12u320.ko screen_mirror=true

echo "⏳ Waiting 5 seconds for driver to stabilize..."
sleep 5

echo "📋 Checking driver status..."
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver loaded successfully"
    echo ""
    echo "📊 Recent kernel messages:"
    dmesg | tail -15 | grep -i "gm12u320\|capture\|frame\|mirror" || echo "No relevant messages"
else
    echo "❌ Driver failed to load"
    dmesg | tail -10
fi

echo ""
echo "🎯 What to expect:"
echo "- If you see 'Screen mirroring enabled': SUCCESS!"
echo "- If you see 'Screen mirroring disabled': FAILED"
echo "- If system freezes: Reboot and use emergency_driver.sh"
echo ""
echo "=== END RELOAD ===" 