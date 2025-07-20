#!/bin/bash

# GM12U320 Framebuffer Clone Script
# Based on slavrn/gm12u320 fbclone but adapted for kernel 6.8
# Usage: sudo ./fbclone_gm12u320.sh [interval_ms]

set -e

# Default interval: 100ms (10 FPS)
INTERVAL=${1:-100}
FB0="/dev/fb0"
PROJECTOR_DEV="/sys/class/graphics/fb1"  # Try to find projector device

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}GM12U320 Framebuffer Clone Script${NC}"
echo -e "${GREEN}Based on slavrn/gm12u320 fbclone${NC}"
echo "=================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping framebuffer clone...${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if main framebuffer exists
if [ ! -c "$FB0" ]; then
    echo -e "${RED}Error: $FB0 not found${NC}"
    exit 1
fi

# Get framebuffer info using fbset
echo -e "${GREEN}Getting framebuffer information...${NC}"
FB0_INFO=$(fbset -fb $FB0 -i 2>/dev/null || echo "")

if [ -z "$FB0_INFO" ]; then
    echo -e "${RED}Error: Cannot get framebuffer info from $FB0${NC}"
    echo -e "${YELLOW}Trying alternative method...${NC}"
    
    # Alternative: try to read framebuffer directly
    FB0_SIZE=$(stat -c %s $FB0 2>/dev/null || echo "0")
    if [ "$FB0_SIZE" -eq 0 ]; then
        echo -e "${RED}Error: Cannot access framebuffer $FB0${NC}"
        exit 1
    fi
    echo -e "${GREEN}Framebuffer size: $FB0_SIZE bytes${NC}"
else
    # Parse resolution from fbset output
    RESOLUTION=$(echo "$FB0_INFO" | grep geometry | awk '{print $2, $3}')
    if [ -z "$RESOLUTION" ]; then
        echo -e "${RED}Error: Cannot parse resolution from $FB0${NC}"
        exit 1
    fi
    
    WIDTH=$(echo $RESOLUTION | awk '{print $1}')
    HEIGHT=$(echo $RESOLUTION | awk '{print $2}')
    BPP=$(echo "$FB0_INFO" | grep bpp | awk '{print $2}')
    
    echo -e "${GREEN}Source resolution: ${WIDTH}x${HEIGHT}, ${BPP}bpp${NC}"
fi

# Target resolution for GM12U320 (reduced for memory constraints)
TARGET_WIDTH=640
TARGET_HEIGHT=480
TARGET_BPP=24

echo -e "${GREEN}Target resolution: ${TARGET_WIDTH}x${TARGET_HEIGHT}, ${TARGET_BPP}bpp${NC}"
echo -e "${GREEN}Interval: ${INTERVAL}ms${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo "=================================="

# Create temporary buffer for conversion
TEMP_BUFFER="/tmp/gm12u320_fb_temp"
TARGET_SIZE=$((TARGET_WIDTH * TARGET_HEIGHT * TARGET_BPP / 8))

# Function to convert RGB565 to RGB24
convert_rgb565_to_rgb24() {
    local input_file="$1"
    local output_file="$2"
    local width="$3"
    local height="$4"
    
    # Use dd to read raw data and convert
    dd if="$input_file" bs=1 count=$((width * height * 2)) 2>/dev/null | \
    while IFS= read -r -n 2 bytes; do
        # Convert 2 bytes to RGB24
        if [ ${#bytes} -eq 2 ]; then
            # Extract RGB565 components
            pixel=$(printf "%02x%02x" "'${bytes:0:1}" "'${bytes:1:1}")
            r=$(( (pixel >> 11) & 0x1F ))
            g=$(( (pixel >> 5) & 0x3F ))
            b=$(( pixel & 0x1F ))
            
            # Convert to 8-bit
            r=$(( r * 255 / 31 ))
            g=$(( g * 255 / 63 ))
            b=$(( b * 255 / 31 ))
            
            # Write RGB24 bytes
            printf "\\$(printf '%03o' $r)"
            printf "\\$(printf '%03o' $g)"
            printf "\\$(printf '%03o' $b)"
        fi
    done > "$output_file"
}

# Function to scale image (simple nearest neighbor)
scale_image() {
    local input_file="$1"
    local output_file="$2"
    local src_width="$3"
    local src_height="$4"
    local dst_width="$5"
    local dst_height="$6"
    
    # For now, just copy the first part of the image
    # This is a simplified scaling - in production you'd want proper scaling
    dd if="$input_file" of="$output_file" bs=1 count=$((dst_width * dst_height * 3)) 2>/dev/null
}

# Main loop
frame_count=0
start_time=$(date +%s)

while true; do
    frame_count=$((frame_count + 1))
    
    # Create temporary files
    temp_fb0="/tmp/fb0_${frame_count}.raw"
    temp_converted="/tmp/converted_${frame_count}.raw"
    
    # Read from main framebuffer
    if dd if="$FB0" of="$temp_fb0" bs=1M conv=notrunc status=none 2>/dev/null; then
        
        # Convert and scale
        if [ ! -z "$BPP" ] && [ "$BPP" -eq 16 ]; then
            # Convert RGB565 to RGB24
            convert_rgb565_to_rgb24 "$temp_fb0" "$temp_converted" "$WIDTH" "$HEIGHT"
        else
            # Assume RGB24 or RGB32, just copy
            dd if="$temp_fb0" of="$temp_converted" bs=1 count=$TARGET_SIZE 2>/dev/null
        fi
        
        # Try to write to projector device
        if [ -w "$PROJECTOR_DEV" ]; then
            dd if="$temp_converted" of="$PROJECTOR_DEV" bs=1M conv=notrunc status=none 2>/dev/null
            echo -e "${GREEN}Frame $frame_count sent to projector${NC}"
        else
            # Try alternative methods
            if [ -w "/dev/fb1" ]; then
                dd if="$temp_converted" of="/dev/fb1" bs=1M conv=notrunc status=none 2>/dev/null
                echo -e "${GREEN}Frame $frame_count sent to /dev/fb1${NC}"
            else
                echo -e "${YELLOW}Frame $frame_count processed but no projector device found${NC}"
            fi
        fi
        
        # Clean up temporary files
        rm -f "$temp_fb0" "$temp_converted"
        
    else
        echo -e "${RED}Error reading from $FB0${NC}"
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
    sleep $(echo "scale=3; $INTERVAL/1000" | bc -l 2>/dev/null || echo "0.1")
done 