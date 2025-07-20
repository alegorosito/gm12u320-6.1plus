#!/bin/bash

# Final Comprehensive Check Script
# Usage: sudo ./final_check.sh

echo "=== FINAL COMPREHENSIVE CHECK ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Checking current driver status..."

# Check if driver is loaded
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver is loaded"
    lsmod | grep "gm12u320"
else
    echo "❌ Driver is not loaded"
    exit 1
fi

echo ""
echo "📊 Recent kernel messages (last 30):"
dmesg | tail -30 | grep -i "gm12u320\|capture\|frame\|mirror" || echo "No relevant messages"

echo ""
echo "🔍 Analyzing messages for patterns:"
echo ""

# Count different message types
MIRROR_ENABLED=$(dmesg | grep -c "Screen mirroring enabled")
MIRROR_DISABLED=$(dmesg | grep -c "Screen mirroring disabled")
CAPTURE_SUCCESS=$(dmesg | grep -c "Captured main screen")
RAINBOW_PATTERN=$(dmesg | grep -c "rainbow pattern")

echo "📈 Message counts:"
echo "- 'Screen mirroring enabled': $MIRROR_ENABLED"
echo "- 'Screen mirroring disabled': $MIRROR_DISABLED"
echo "- 'Captured main screen': $CAPTURE_SUCCESS"
echo "- 'rainbow pattern': $RAINBOW_PATTERN"

echo ""
echo "🎯 Current status analysis:"

if [ $MIRROR_ENABLED -gt 0 ]; then
    echo "✅ MIRRORING IS ENABLED in logs"
else
    echo "❌ MIRRORING IS NOT ENABLED in logs"
fi

if [ $CAPTURE_SUCCESS -gt 0 ]; then
    echo "✅ SCREEN CAPTURE IS WORKING"
else
    echo "❌ SCREEN CAPTURE IS NOT WORKING"
fi

if [ $RAINBOW_PATTERN -gt 0 ]; then
    echo "❌ RAINBOW PATTERN IS BEING USED"
else
    echo "✅ RAINBOW PATTERN IS NOT BEING USED"
fi

echo ""
echo "🔧 Recommendations:"

if [ $MIRROR_DISABLED -gt 0 ] && [ $MIRROR_ENABLED -eq 0 ]; then
    echo "❌ Driver needs to be recompiled and reloaded"
    echo "   Run: make clean && make && sudo ./force_reload.sh"
elif [ $MIRROR_ENABLED -gt 0 ] && [ $CAPTURE_SUCCESS -eq 0 ]; then
    echo "❌ Mirroring enabled but capture not working"
    echo "   Check /dev/fb0 access and permissions"
elif [ $CAPTURE_SUCCESS -gt 0 ] && [ $RAINBOW_PATTERN -gt 0 ]; then
    echo "❌ Capture working but rainbow pattern still used"
    echo "   Check the goto rainbow_pattern issue in code"
else
    echo "✅ Everything looks good, check projector connection"
fi

echo ""
echo "=== END FINAL CHECK ===" 