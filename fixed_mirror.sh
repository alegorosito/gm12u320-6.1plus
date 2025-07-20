#!/bin/bash

# Fixed GM12U320 Screen Mirror Script
# Usage: sudo ./fixed_mirror.sh [interval_ms]

# Default interval: 200ms (5 FPS) - slower to avoid freezing
INTERVAL=${1:-200}
FB0="/dev/fb0"
FB1="/dev/fb1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Fixed GM12U320 Screen Mirror Script${NC}"
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

# Get framebuffer info using fbset
echo -e "${GREEN}Getting framebuffer information...${NC}"

# Get fb0 info
FB0_INFO=$(fbset -fb $FB0 -i 2>/dev/null)
if [ -z "$FB0_INFO" ]; then
    echo -e "${RED}Error: Cannot get info from $FB0${NC}"
    exit 1
fi

# Get fb1 info
FB1_INFO=$(fbset -fb $FB1 -i 2>/dev/null)
if [ -z "$FB1_INFO" ]; then
    echo -e "${RED}Error: Cannot get info from $FB1${NC}"
    exit 1
fi

# Parse sizes from fbset output
FB0_SIZE=$(echo "$FB0_INFO" | grep "Size" | awk '{print $3}')
FB1_SIZE=$(echo "$FB1_INFO" | grep "Size" | awk '{print $3}')

# Parse resolutions
FB0_RES=$(echo "$FB0_INFO" | grep "geometry" | awk '{print $2, $3}')
FB1_RES=$(echo "$FB1_INFO" | grep "geometry" | awk '{print $2, $3}')

echo -e "${GREEN}Source framebuffer: ${FB0_RES} (${FB0_SIZE} bytes)${NC}"
echo -e "${GREEN}Target framebuffer: ${FB1_RES} (${FB1_SIZE} bytes)${NC}"
echo -e "${GREEN}Interval: ${INTERVAL}ms${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo "=================================="

# Main loop - copy only what fits
frame_count=0
start_time=$(date +%s)

while true; do
    frame_count=$((frame_count + 1))
    
    # Copy from fb0 to fb1, but only copy the smaller size
    # This will copy the top-left portion of the screen
    if dd if="$FB0" of="$FB1" bs=1 count="$FB1_SIZE" conv=notrunc status=none 2>/dev/null; then
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
            echo -e "${BLUE}FPS: $fps${NC}"
        fi
    fi
    
    # Sleep for the specified interval
    sleep $(echo "scale=3; $INTERVAL/1000" | bc -l 2>/dev/null || echo "0.2")
done 