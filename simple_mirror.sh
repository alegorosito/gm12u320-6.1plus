#!/bin/bash

# Simple GM12U320 Screen Mirror Script
# Usage: sudo ./simple_mirror.sh [interval_ms]

# Default interval: 200ms (5 FPS) - slower to avoid freezing
INTERVAL=${1:-200}
FB0="/dev/fb0"
FB1="/dev/fb1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Simple GM12U320 Screen Mirror Script${NC}"
echo "=================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping screen mirror...${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if framebuffer devices exist
if [ ! -c "$FB0" ]; then
    echo -e "${RED}Error: $FB0 not found${NC}"
    exit 1
fi

if [ ! -w "$FB1" ]; then
    echo -e "${RED}Error: $FB1 not found or not writable${NC}"
    exit 1
fi

# Get framebuffer info
echo -e "${GREEN}Getting framebuffer information...${NC}"
FB0_SIZE=$(stat -c %s $FB0 2>/dev/null || echo "0")
FB1_SIZE=$(stat -c %s $FB1 2>/dev/null || echo "0")

echo -e "${GREEN}Source framebuffer size: $FB0_SIZE bytes${NC}"
echo -e "${GREEN}Target framebuffer size: $FB1_SIZE bytes${NC}"
echo -e "${GREEN}Interval: ${INTERVAL}ms${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo "=================================="

# Main loop - simple copy approach
frame_count=0
start_time=$(date +%s)

while true; do
    frame_count=$((frame_count + 1))
    
    # Simple copy: read from fb0 and write to fb1
    if dd if="$FB0" of="$FB1" bs=1M conv=notrunc status=none 2>/dev/null; then
        echo -e "${GREEN}Frame $frame_count copied successfully${NC}"
    else
        echo -e "${RED}Error copying frame $frame_count${NC}"
        # Don't exit on error, just continue
    fi
    
    # Calculate and display FPS every 10 frames
    if [ $((frame_count % 10)) -eq 0 ]; then
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -gt 0 ]; then
            fps=$(echo "scale=1; $frame_count / $elapsed" | bc -l 2>/dev/null || echo "0")
            echo -e "${GREEN}FPS: $fps${NC}"
        fi
    fi
    
    # Sleep for the specified interval
    sleep $(echo "scale=3; $INTERVAL/1000" | bc -l 2>/dev/null || echo "0.2")
done 