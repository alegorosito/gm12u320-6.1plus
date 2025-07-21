#!/bin/bash

# GM12U320 Projector Mirror Script using v4l2loopback
# This script creates a virtual video device and mirrors screen to it

echo "🎥 GM12U320 Projector Mirror Script (v4l2loopback)"
echo "=================================================="

# Check if v4l2loopback is installed
if ! modinfo v4l2loopback &> /dev/null; then
    echo "❌ v4l2loopback not found. Installing..."
    sudo apt update
    sudo apt install -y v4l2loopback-dkms
fi

# Load v4l2loopback module
if ! lsmod | grep -q v4l2loopback; then
    echo "🔄 Loading v4l2loopback module..."
    sudo modprobe v4l2loopback video_nr=10 card_label="GM12U320_Mirror" width=800 height=600
fi

# Check if driver is loaded
if ! lsmod | grep -q gm12u320; then
    echo "❌ GM12U320 driver not loaded. Loading driver..."
    sudo modprobe gm12u320
    sleep 2
fi

# Check if virtual video device exists
if [ ! -e "/dev/video10" ]; then
    echo "❌ Virtual video device /dev/video10 not found"
    exit 1
fi

echo "✅ Virtual video device created at /dev/video10"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping mirror..."
    kill $FFMPEG_PID 2>/dev/null
    sudo modprobe -r v4l2loopback 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🔄 Starting screen capture to virtual device..."
echo "Press Ctrl+C to stop"
echo ""

# Start FFmpeg to capture screen and send to virtual device
ffmpeg -f x11grab -r 10 -s 800x600 -i :0.0 -f v4l2 -pix_fmt yuv420p -s 800x600 -r 10 /dev/video10 &
FFMPEG_PID=$!

echo "🎬 v4l2loopback mirror started! PID: $FFMPEG_PID"
echo "📺 Screen is now being captured to /dev/video10"
echo "📹 You can view it with: ffplay /dev/video10"
echo ""

# Wait for the FFmpeg process
wait $FFMPEG_PID 