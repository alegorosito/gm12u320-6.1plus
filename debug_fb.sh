#!/bin/bash

# Debug Framebuffer Script
# Usage: sudo ./debug_fb.sh

echo "=== FRAMEBUFFER DEBUG SCRIPT ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Checking framebuffer devices..."

# Check /dev/fb0
echo ""
echo "=== /dev/fb0 (Main Display) ==="
if [ -c "/dev/fb0" ]; then
    echo "✅ /dev/fb0 exists"
    ls -la /dev/fb0
    
    # Check size
    FB0_SIZE=$(stat -c %s /dev/fb0 2>/dev/null || echo "ERROR")
    echo "📏 Size: $FB0_SIZE bytes"
    
    # Check if readable
    if [ -r "/dev/fb0" ]; then
        echo "✅ Readable"
    else
        echo "❌ Not readable"
    fi
    
    # Try to get info with fbset
    echo ""
    echo "📊 fbset info:"
    fbset -fb /dev/fb0 -i 2>/dev/null || echo "❌ fbset failed"
    
else
    echo "❌ /dev/fb0 does not exist"
fi

# Check /dev/fb1
echo ""
echo "=== /dev/fb1 (Projector) ==="
if [ -c "/dev/fb1" ]; then
    echo "✅ /dev/fb1 exists"
    ls -la /dev/fb1
    
    # Check size
    FB1_SIZE=$(stat -c %s /dev/fb1 2>/dev/null || echo "ERROR")
    echo "📏 Size: $FB1_SIZE bytes"
    
    # Check if writable
    if [ -w "/dev/fb1" ]; then
        echo "✅ Writable"
    else
        echo "❌ Not writable"
    fi
    
    # Try to get info with fbset
    echo ""
    echo "📊 fbset info:"
    fbset -fb /dev/fb1 -i 2>/dev/null || echo "❌ fbset failed"
    
else
    echo "❌ /dev/fb1 does not exist"
fi

# Check all framebuffers
echo ""
echo "=== All Framebuffer Devices ==="
ls -la /dev/fb* 2>/dev/null || echo "❌ No framebuffer devices found"

# Check kernel messages
echo ""
echo "=== Recent Kernel Messages ==="
dmesg | tail -20 | grep -i "fb\|framebuffer\|gm12u320" || echo "No relevant kernel messages"

# Check loaded modules
echo ""
echo "=== Loaded Graphics Modules ==="
lsmod | grep -i "drm\|fb\|gm12u320" || echo "No relevant modules loaded"

echo ""
echo "=== END DEBUG ===" 