#!/bin/bash

# Check Screen Mirroring Status
# Usage: sudo ./check_mirror.sh

echo "=== CHECK SCREEN MIRRORING STATUS ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Checking driver status..."

# Check if driver is loaded
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver is loaded"
    lsmod | grep "gm12u320"
else
    echo "❌ Driver is not loaded"
    exit 1
fi

echo ""
echo "📊 Recent kernel messages (last 20):"
dmesg | tail -20 | grep -i "gm12u320\|capture\|frame\|mirror" || echo "No relevant messages"

echo ""
echo "🔍 Looking for specific patterns:"
echo "✅ 'Screen mirroring enabled' = SUCCESS"
echo "❌ 'Screen mirroring disabled' = FAILED"
echo "✅ 'Captured main screen' = WORKING"
echo "❌ 'rainbow pattern' = FALLBACK"

echo ""
echo "📋 Current status:"
if dmesg | tail -10 | grep -q "Screen mirroring enabled"; then
    echo "🎉 MIRRORING IS ENABLED!"
elif dmesg | tail -10 | grep -q "Screen mirroring disabled"; then
    echo "❌ MIRRORING IS DISABLED"
else
    echo "❓ UNKNOWN STATUS"
fi

echo ""
echo "=== END CHECK ===" 