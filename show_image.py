#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Handles 800x600 resolution with 2560 byte stride (2400 data + 160 padding)
"""

import numpy as np
import os
import sys
from PIL import Image
import requests
import io

# Projector specifications
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
BYTES_PER_PIXEL = 3
DATA_BYTES_PER_LINE = PROJECTOR_WIDTH * BYTES_PER_PIXEL  # 2400 bytes
STRIDE_BYTES_PER_LINE = 2560  # 2400 data + 160 padding
PADDING_BYTES_PER_LINE = STRIDE_BYTES_PER_LINE - DATA_BYTES_PER_LINE  # 160 bytes
TOTAL_FILE_SIZE = STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT  # 1,536,000 bytes

def load_image_from_path(image_path):
    """Load image from local file path"""
    try:
        print(f"Loading image from: {image_path}")
        image = Image.open(image_path)
        print(f"Image loaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

def download_image(url):
    """Download image from URL"""
    try:
        print(f"Downloading image from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        print(f"Image downloaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def resize_image(image, target_width, target_height):
    """Resize image to exact projector resolution"""
    try:
        resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        print(f"Image resized to: {target_width}x{target_height}")
        return resized_image
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None

def create_rgb_buffer_with_stride(image):
    """Convert PIL image to RGB buffer with proper stride and padding"""
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        array = np.array(image, dtype=np.uint8)
        
        # Create buffer with proper stride
        buffer = bytearray()
        
        for y in range(PROJECTOR_HEIGHT):
            # Add data bytes for this line
            for x in range(PROJECTOR_WIDTH):
                r, g, b = array[y, x]
                buffer.extend([r, g, b])
            
            # Add padding bytes to reach stride
            buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
        
        print(f"Buffer created: {len(buffer)} bytes")
        print(f"Expected size: {TOTAL_FILE_SIZE} bytes")
        print(f"Data bytes per line: {DATA_BYTES_PER_LINE}")
        print(f"Padding bytes per line: {PADDING_BYTES_PER_LINE}")
        print(f"Total stride per line: {STRIDE_BYTES_PER_LINE}")
        
        return bytes(buffer)
    except Exception as e:
        print(f"Error creating RGB buffer: {e}")
        return None

def create_test_pattern():
    """Create test pattern with proper stride"""
    try:
        buffer = bytearray()
        
        for y in range(PROJECTOR_HEIGHT):
            # Add data bytes for this line
            for x in range(PROJECTOR_WIDTH):
                r = (x * 255) // PROJECTOR_WIDTH
                g = (y * 255) // PROJECTOR_HEIGHT
                b = 128
                buffer.extend([r, g, b])
            
            # Add padding bytes to reach stride
            buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
        
        print(f"Test pattern created: {len(buffer)} bytes")
        return bytes(buffer)
    except Exception as e:
        print(f"Error creating test pattern: {e}")
        return None

def write_to_file(data, filename="/tmp/gm12u320_image.rgb"):
    """Write data to file with validation"""
    try:
        with open(filename, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        # Validate file size
        file_size = os.path.getsize(filename)
        print(f"File written: {filename}")
        print(f"File size: {file_size} bytes")
        
        if file_size == TOTAL_FILE_SIZE:
            print("File size validation: PASSED")
            return True
        else:
            print(f"File size validation: FAILED (expected {TOTAL_FILE_SIZE}, got {file_size})")
            return False
            
    except Exception as e:
        print(f"Error writing to file: {e}")
        return False

def main():
    print("GM12U320 Projector Image Display")
    print("=================================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("Projector device /dev/dri/card2 not found")
        print("Please make sure the GM12U320 driver is loaded")
        return 1
    
    print("Projector device found: /dev/dri/card2")
    
    # Get image source from command line or use test pattern
    if len(sys.argv) > 1:
        image_source = sys.argv[1]
        
        # Check if it's a local file or URL
        if os.path.exists(image_source):
            print(f"Using local image file: {image_source}")
            image = load_image_from_path(image_source)
        elif image_source.startswith(('http://', 'https://')):
            print(f"Using custom image URL: {image_source}")
            image = download_image(image_source)
        else:
            print(f"Invalid image source: {image_source}")
            image = None
            
        if image is None:
            print("Using test pattern instead")
            data = create_test_pattern()
        else:
            # Resize image
            resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized_image is None:
                print("Using test pattern instead")
                data = create_test_pattern()
            else:
                # Convert to RGB buffer with stride
                data = create_rgb_buffer_with_stride(resized_image)
                if data is None:
                    print("Using test pattern instead")
                    data = create_test_pattern()
    else:
        print("Creating test pattern")
        data = create_test_pattern()
    
    if not data:
        print("Failed to create image data")
        return 1
    
    # Write to file
    if not write_to_file(data):
        print("Failed to write image to file")
        return 1
    
    print("Image sent to projector successfully")
    print("The driver will read the image from /tmp/gm12u320_image.rgb")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping image display")
        try:
            os.remove("/tmp/gm12u320_image.rgb")
            print("Image file removed, projector will show test pattern")
        except:
            pass
        return 0

if __name__ == "__main__":
    sys.exit(main()) 