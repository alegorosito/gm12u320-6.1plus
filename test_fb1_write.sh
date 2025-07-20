#!/bin/bash

# Test /dev/fb1 Write Access
# Usage: sudo ./test_fb1_write.sh

echo "=== /dev/fb1 WRITE TEST ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Testing /dev/fb1 write access..."

# Check if device exists
if [ ! -c "/dev/fb1" ]; then
    echo "❌ /dev/fb1 does not exist"
    exit 1
fi

echo "✅ /dev/fb1 exists"

# Check permissions
ls -la /dev/fb1

# Test 1: Try to write a small amount of data
echo ""
echo "=== Test 1: Write 1024 bytes ==="
if dd if=/dev/zero of=/dev/fb1 bs=1024 count=1 2>/dev/null; then
    echo "✅ Successfully wrote 1024 bytes"
else
    echo "❌ Failed to write 1024 bytes"
fi

# Test 2: Try to write with different methods
echo ""
echo "=== Test 2: Write with head ==="
if head -c 1024 /dev/zero > /dev/fb1 2>/dev/null; then
    echo "✅ Successfully wrote with head"
else
    echo "❌ Failed to write with head"
fi

# Test 3: Try to write with cat
echo ""
echo "=== Test 3: Write with cat ==="
if cat /dev/zero | head -c 1024 > /dev/fb1 2>/dev/null; then
    echo "✅ Successfully wrote with cat"
else
    echo "❌ Failed to write with cat"
fi

# Test 4: Check if device is busy
echo ""
echo "=== Test 4: Check device usage ==="
lsof /dev/fb1 2>/dev/null || echo "No processes using /dev/fb1"

# Test 5: Check kernel messages
echo ""
echo "=== Test 5: Kernel messages ==="
dmesg | tail -5 | grep -i "fb1\|gm12u320" || echo "No relevant messages"

echo ""
echo "=== END TEST ===" 