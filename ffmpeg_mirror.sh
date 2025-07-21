#!/bin/bash

# GM12U320 Projector Mirror Script using FFmpeg
# This script captures the screen and sends it to the projector

echo "🎥 GM12U320 Projector Mirror Script (FFmpeg)"
echo "============================================"

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
echo "🔄 Starting screen capture and projection..."
echo "Press Ctrl+C to stop"
echo ""

# Start FFmpeg to capture screen and send to projector
# This will capture the X11 display and send it to the projector
ffmpeg -f x11grab -r 10 -s 800x600 -i :0.0 -f rawvideo -pix_fmt rgb24 -s 800x600 -r 10 -y /dev/dri/card2 &
FFMPEG_PID=$!

echo "🎬 FFmpeg mirror started! PID: $FFMPEG_PID"
echo "📺 Screen is now being captured and sent to the GM12U320 projector"
echo ""

# Wait for the FFmpeg process
wait $FFMPEG_PID 