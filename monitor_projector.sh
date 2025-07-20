#!/bin/bash

# Monitor Projector Status Script
# Usage: sudo ./monitor_projector.sh

echo "=== PROJECTOR MONITOR SCRIPT ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Monitoring projector status..."
echo "Press Ctrl+C to stop"
echo ""

# Monitor logs in real-time
echo "=== Real-time Kernel Logs ==="
echo "Looking for gm12u320 messages..."
echo ""

# Use tail -f to monitor logs
tail -f /var/log/kern.log 2>/dev/null | grep --line-buffered -i "gm12u320\|frame\|capture\|scale" || \
dmesg | tail -20 | grep -i "gm12u320\|frame\|capture\|scale" 