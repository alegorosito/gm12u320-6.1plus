#!/bin/bash

# GM12U320 Projector Mirror Script - FFmpeg Framebuffer
# This script uses FFmpeg to capture from framebuffer and send to projector

echo "🎥 GM12U320 Projector Mirror Script (FFmpeg FB)"
echo "==============================================="

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Installing..."
    sudo apt update
    sudo apt install -y ffmpeg
fi

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
    kill $FFMPEG_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🔄 Starting FFmpeg framebuffer mirror..."
echo "Press Ctrl+C to stop"
echo ""

# Get framebuffer information
FB_INFO=$(sudo fbset -i 2>/dev/null | grep -E "(geometry|depth)" | tr '\n' ' ')
echo "📺 Framebuffer info: $FB_INFO"

# Start FFmpeg to capture from framebuffer and send to projector
# Assuming 800x600 resolution, adjust as needed
ffmpeg -f fbdev -framerate 10 -video_size 800x600 -i /dev/fb0 -f rawvideo -pix_fmt rgb24 -s 800x600 -r 10 -y /dev/dri/card2 &
FFMPEG_PID=$!

echo "🎬 FFmpeg framebuffer mirror started! PID: $FFMPEG_PID"
echo "📺 Framebuffer is now being captured and sent to the GM12U320 projector"
echo ""

# Wait for the FFmpeg process
wait $FFMPEG_PID 