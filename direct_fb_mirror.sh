#!/bin/bash

# GM12U320 Projector Mirror Script - Direct Framebuffer
# This script captures directly from /dev/fb0 and sends to projector

echo "🎥 GM12U320 Projector Mirror Script (Direct FB)"
echo "==============================================="

# Check if driver is loaded
if ! lsmod | grep -q gm12u320; then
    echo "❌ GM12U320 driver not loaded. Loading driver..."
    sudo modprobe gm12u320
    sleep 2
fi

# Check if projector device exists
if [ ! -e "/dev/dri/card2" ]; then
    echo "❌ Projector device /dev/dri/card2 not found"
    echo "Please check if the GM12U320 device is connected"
    exit 1
fi

echo "✅ GM12U320 projector detected at /dev/dri/card2"

# Check if main framebuffer exists
if [ ! -e "/dev/fb0" ]; then
    echo "❌ Main framebuffer /dev/fb0 not found"
    exit 1
fi

echo "✅ Main framebuffer detected at /dev/fb0"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping mirror..."
    kill $MIRROR_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🔄 Starting direct framebuffer mirror..."
echo "Press Ctrl+C to stop"
echo ""

# Get framebuffer information
FB_INFO=$(sudo fbset -i 2>/dev/null | grep -E "(geometry|depth)" | tr '\n' ' ')
echo "📺 Framebuffer info: $FB_INFO"

# Start mirroring loop
MIRROR_PID=$$
(
    while true; do
        # Copy framebuffer to projector using dd
        if sudo dd if=/dev/fb0 of=/dev/dri/card2 bs=1M 2>/dev/null; then
            echo "📺 Frame sent to projector"
        else
            echo "⚠️  Frame copy failed, retrying..."
        fi
        sleep 0.1  # 10 FPS
    done
) &
MIRROR_PID=$!

echo "🎬 Direct mirror started! PID: $MIRROR_PID"
echo "📺 Main framebuffer is now being mirrored to the GM12U320 projector"
echo ""

# Wait for the mirror process
wait $MIRROR_PID 