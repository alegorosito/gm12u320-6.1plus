#!/bin/bash

# Check /dev/fb1 Status Script
# Usage: sudo ./check_fb1.sh

echo "=== /dev/fb1 STATUS CHECK ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Checking /dev/fb1 status..."

# Check if device exists
if [ -c "/dev/fb1" ]; then
    echo "✅ /dev/fb1 exists"
else
    echo "❌ /dev/fb1 does not exist"
    exit 1
fi

# Check permissions
echo ""
echo "=== Permissions ==="
ls -la /dev/fb1

# Check owner and group
OWNER=$(stat -c %U /dev/fb1)
GROUP=$(stat -c %G /dev/fb1)
echo "Owner: $OWNER"
echo "Group: $GROUP"

# Check if we can write
if [ -w "/dev/fb1" ]; then
    echo "✅ /dev/fb1 is writable"
else
    echo "❌ /dev/fb1 is NOT writable"
fi

# Check if we can read
if [ -r "/dev/fb1" ]; then
    echo "✅ /dev/fb1 is readable"
else
    echo "❌ /dev/fb1 is NOT readable"
fi

# Check device major/minor
MAJOR=$(stat -c %t /dev/fb1)
MINOR=$(stat -c %T /dev/fb1)
echo "Device: $MAJOR:$MINOR"

# Try to get info with fbset
echo ""
echo "=== fbset info ==="
fbset -fb /dev/fb1 -i 2>/dev/null || echo "❌ fbset failed"

# Try to write a small test
echo ""
echo "=== Writing test ==="
if echo "test" > /dev/fb1 2>/dev/null; then
    echo "✅ Can write test data to /dev/fb1"
else
    echo "❌ Cannot write test data to /dev/fb1"
fi

# Check kernel messages for fb1
echo ""
echo "=== Kernel messages for fb1 ==="
dmesg | grep -i "fb1\|gm12u320" | tail -10 || echo "No relevant messages"

# Check if device is busy
echo ""
echo "=== Device usage ==="
lsof /dev/fb1 2>/dev/null || echo "No processes using /dev/fb1"

echo ""
echo "=== END CHECK ===" 