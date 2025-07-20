#!/bin/bash

# Emergency Driver Load Script
# Usage: sudo ./emergency_driver.sh

echo "=== EMERGENCY DRIVER LOAD ==="
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

echo "🔄 Loading driver with screen_mirror=false..."
insmod gm12u320.ko screen_mirror=false

echo "⏳ Waiting 3 seconds..."
sleep 3

echo "📋 Checking driver status..."
if lsmod | grep -q "gm12u320"; then
    echo "✅ Driver loaded successfully"
    dmesg | tail -5 | grep -i "gm12u320"
else
    echo "❌ Driver failed to load"
    dmesg | tail -10
fi

echo ""
echo "=== END EMERGENCY LOAD ===" 