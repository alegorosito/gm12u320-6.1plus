#!/bin/bash

# Enable Screen Mirroring Script
# Usage: sudo ./enable_mirror.sh

echo "=== ENABLE SCREEN MIRRORING ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔄 Unloading current driver..."
rmmod gm12u320 2>/dev/null || echo "Driver not loaded"

echo "⏳ Waiting 2 seconds..."
sleep 2

echo "🔄 Loading driver with screen_mirror=true..."
insmod gm12u320.ko screen_mirror=true

echo "⏳ Waiting 5 seconds for driver to stabilize..."
sleep 5

echo "📋 Checking driver status..."
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver loaded successfully"
    echo ""
    echo "📊 Recent kernel messages:"
    dmesg | tail -10 | grep -i "gm12u320\|capture\|frame" || echo "No relevant messages"
else
    echo "❌ Driver failed to load"
    dmesg | tail -10
fi

echo ""
echo "🎯 What to expect:"
echo "- If successful: Proyector should show your screen content"
echo "- If failed: Proyector will show rainbow pattern"
echo "- If system freezes: Reboot and use emergency_driver.sh"
echo ""
echo "=== END ENABLE MIRROR ===" 