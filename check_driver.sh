#!/bin/bash

# Check and Fix Driver Script
# Usage: sudo ./check_driver.sh

echo "=== GM12U320 DRIVER CHECK SCRIPT ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

echo "🔍 Checking driver status..."

# Check if module is loaded
echo ""
echo "=== Module Status ==="
if lsmod | grep -q "gm12u320"; then
    echo "✅ gm12u320 module is loaded"
    lsmod | grep "gm12u320"
else
    echo "❌ gm12u320 module is NOT loaded"
fi

# Check USB device
echo ""
echo "=== USB Device Status ==="
if lsusb | grep -i "gm12u320\|projector"; then
    echo "✅ USB device detected"
    lsusb | grep -i "gm12u320\|projector"
else
    echo "❌ USB device not found"
    echo "📋 All USB devices:"
    lsusb
fi

# Check kernel messages for driver
echo ""
echo "=== Driver Kernel Messages ==="
dmesg | grep -i "gm12u320" | tail -10 || echo "No gm12u320 messages found"

# Check if we need to reload the driver
echo ""
echo "=== Driver Reload Options ==="
echo "1. Unload and reload driver"
echo "2. Check framebuffer devices after reload"
echo "3. Exit"

read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo "🔄 Unloading driver..."
        rmmod gm12u320 2>/dev/null || echo "Driver not loaded or already unloaded"
        
        echo "🔄 Loading driver..."
        modprobe gm12u320
        
        echo "⏳ Waiting 3 seconds..."
        sleep 3
        
        echo "✅ Driver reloaded"
        ;;
    2)
        echo "📋 Current framebuffer devices:"
        ls -la /dev/fb* 2>/dev/null || echo "No framebuffer devices"
        ;;
    3)
        echo "👋 Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid option"
        ;;
esac

echo ""
echo "=== END CHECK ===" 