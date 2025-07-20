#!/bin/bash

# Screen Mirror Script for GM12U320 Projector
# More efficient than "cat /dev/fb0 > /dev/fb1"
# Usage: sudo ./screen_mirror.sh [interval_ms]

set -e

# Default interval: 100ms (10 FPS)
INTERVAL=${1:-100}
FB0="/dev/fb0"
FB1="/dev/fb1"

# Check if framebuffer devices exist
if [ ! -c "$FB0" ]; then
    echo "Error: $FB0 not found"
    exit 1
fi

if [ ! -w "$FB1" ]; then
    echo "Error: $FB1 not found or not writable"
    exit 1
fi

# Get framebuffer info
FB0_INFO=$(fbset -fb $FB0 -i 2>/dev/null || echo "")
if [ -z "$FB0_INFO" ]; then
    echo "Error: Cannot get framebuffer info from $FB0"
    exit 1
fi

# Parse resolution from fbset output
RESOLUTION=$(echo "$FB0_INFO" | grep geometry | awk '{print $2, $3}')
if [ -z "$RESOLUTION" ]; then
    echo "Error: Cannot parse resolution from $FB0"
    exit 1
fi

WIDTH=$(echo $RESOLUTION | awk '{print $1}')
HEIGHT=$(echo $RESOLUTION | awk '{print $2}')

echo "Starting screen mirror: ${WIDTH}x${HEIGHT} -> projector"
echo "Interval: ${INTERVAL}ms"
echo "Press Ctrl+C to stop"

# Function to cleanup on exit
cleanup() {
    echo -e "\nStopping screen mirror..."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main loop with efficient copying
while true; do
    # Use dd for efficient copying with status
    dd if="$FB0" of="$FB1" bs=1M conv=notrunc status=none 2>/dev/null
    
    # Sleep for the specified interval
    sleep $(echo "scale=3; $INTERVAL/1000" | bc -l 2>/dev/null || echo "0.1")
done 