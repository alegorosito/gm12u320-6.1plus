#!/bin/bash

# Force Reload Driver with Screen Mirroring
# Usage: sudo ./force_reload.sh

echo "=== FORCE RELOAD DRIVER WITH MIRRORING ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔄 Checking current driver status..."
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver is currently loaded"
    lsmod | grep "gm12u320"
else
    echo "❌ Driver is not loaded"
fi

echo ""
echo "🔄 Stopping any processes using the driver..."
# Kill any processes that might be using the framebuffer
pkill -f "fb" 2>/dev/null || echo "No fb processes found"
sleep 1

echo "🔄 Force unloading current driver..."
rmmod -f gm12u320 2>/dev/null || echo "Force unload failed, trying normal unload"
rmmod gm12u320 2>/dev/null || echo "Normal unload also failed"

echo "⏳ Waiting 5 seconds..."
sleep 5

echo "🔄 Checking if driver is still loaded..."
if lsmod | grep -q "gm12u320"; then
    echo "❌ Driver is still loaded, trying more aggressive approach..."
    echo "🔄 Rebooting system in 10 seconds to force reload..."
    echo "Press Ctrl+C to cancel"
    sleep 10
    reboot
else
    echo "✅ Driver successfully unloaded"
fi

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
echo "=== END FORCE RELOAD ===" 