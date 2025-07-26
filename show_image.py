#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Handles 800x600 resolution with 2562 byte stride (2400 data + 162 padding)
Can display images from file, URL, or capture screen continuously

Requirements:
- PIL (Pillow) with ImageGrab support
- On Linux: may need additional packages for screen capture
- On macOS: requires screen recording permissions
- On Windows: should work out of the box
"""

import numpy as np
import os
import sys
import time
import subprocess
from PIL import Image, ImageGrab
import requests
import io

# Projector specifications
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
BYTES_PER_PIXEL = 3
DATA_BYTES_PER_LINE = PROJECTOR_WIDTH * BYTES_PER_PIXEL  # 2400 bytes
STRIDE_BYTES_PER_LINE = 2562  # 2400 data + 162 padding (optimized)
PADDING_BYTES_PER_LINE = STRIDE_BYTES_PER_LINE - DATA_BYTES_PER_LINE  # 162 bytes
TOTAL_FILE_SIZE = STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT  # 1,537,200 bytes

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

def create_rgb_buffer_with_stride(image, verbose=True):
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
                # Use BGR order (test 2 was correct)
                buffer.extend([b, g, r])
            
            # Add padding bytes to reach stride
            buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
        
        if verbose:
            print(f"Buffer created: {len(buffer)} bytes")
            print(f"Expected size: {TOTAL_FILE_SIZE} bytes")
            print(f"Data bytes per line: {DATA_BYTES_PER_LINE}")
            print(f"Padding bytes per line: {PADDING_BYTES_PER_LINE}")
            print(f"Total stride per line: {STRIDE_BYTES_PER_LINE}")
            print(f"Color order: BGR (test 2)")
        
        return bytes(buffer)
    except Exception as e:
        print(f"Error creating RGB buffer: {e}")
        return None

def capture_screen():
    """Capture screen using PIL ImageGrab (cross-platform)"""
    try:
        # Capture the entire screen
        image = ImageGrab.grab()
        return image
    except Exception as e:
        print(f"❌ Screen capture error: {e}")
        return None

def create_test_pattern(frame_number=0):
    """Create animated test pattern with proper stride"""
    try:
        buffer = bytearray()
        
        for y in range(PROJECTOR_HEIGHT):
            # Add data bytes for this line
            for x in range(PROJECTOR_WIDTH):
                # Create animated pattern
                r = (x * 255 + frame_number * 10) % 256
                g = (y * 255 + frame_number * 15) % 256
                b = (128 + frame_number * 20) % 256
                # Use BGR order (test 2 was correct)
                buffer.extend([b, g, r])
            
            # Add padding bytes to reach stride
            buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
        
        return bytes(buffer)
    except Exception as e:
        print(f"Error creating test pattern: {e}")
        return None

def write_to_file(data, filename="/tmp/gm12u320_image.rgb", verbose=True):
    """Write data to file with validation"""
    try:
        with open(filename, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        # Validate file size
        file_size = os.path.getsize(filename)
        
        if verbose:
            print(f"File written: {filename}")
            print(f"File size: {file_size} bytes")
        
        if file_size == TOTAL_FILE_SIZE:
            if verbose:
                print("File size validation: PASSED")
            return True
        else:
            if verbose:
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
    
    # Show usage if no arguments provided
    if len(sys.argv) == 1:
        print("\nUsage:")
        print("  python3 show_image.py [FPS] [source]")
        print("\nExamples:")
        print("  python3 show_image.py 10 live          # Live screen capture at 10 FPS")
        print("  python3 show_image.py 15 continuous    # Live screen capture at 15 FPS")
        print("  python3 show_image.py 10 screen        # Single screen capture at 10 FPS")
        print("  python3 show_image.py 10 image.jpg     # Static image at 10 FPS")
        print("  python3 show_image.py                  # Test pattern at 10 FPS")
        print("\nPress Ctrl+C to stop")
        print()
    
    # Parse command line arguments
    fps = 10  # Default FPS
    image_source = None
    continuous_capture = False
    
    if len(sys.argv) > 1:
        # Check if first argument is FPS
        try:
            fps = float(sys.argv[1])
            if fps <= 0 or fps > 60:
                print("FPS must be between 0.1 and 60")
                return 1
            print(f"Using FPS: {fps}")
            
            # Check if second argument is image source
            if len(sys.argv) > 2:
                image_source = sys.argv[2]
        except ValueError:
            # First argument is not FPS, treat as image source
            image_source = sys.argv[1]
    
    # Calculate frame interval
    frame_interval = 1.0 / fps
    print(f"Frame interval: {frame_interval:.3f} seconds")
    
    # Check for continuous capture mode
    if image_source == "live" or image_source == "continuous":
        continuous_capture = True
        print("🎥 Continuous screen capture mode enabled")
        print(f"📸 Capturing screen at {fps} FPS")
    elif image_source:
        if image_source == "screen" or image_source == "capture":
            print("Capturing single screen for projector")
            image = capture_screen()
        elif os.path.exists(image_source):
            print(f"Using local image file: {image_source}")
            image = load_image_from_path(image_source)
        elif image_source.startswith(('http://', 'https://')):
            print(f"Using custom image URL: {image_source}")
            image = download_image(image_source)
        else:
            print(f"Invalid image source: {image_source}")
            print("Usage examples:")
            print("  python3 show_image.py 10 live          # Live capture at 10 FPS")
            print("  python3 show_image.py 15 continuous    # Live capture at 15 FPS")
            print("  python3 show_image.py 10 screen        # Single screen capture at 10 FPS")
            print("  python3 show_image.py 10 image.jpg     # Static image at 10 FPS")
            print("  python3 show_image.py                  # Test pattern at 10 FPS")
            image = None
            
        if image is None:
            print("Using animated test pattern instead")
            use_static_image = False
        else:
            # Resize image
            resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized_image is None:
                print("Using animated test pattern instead")
                use_static_image = False
            else:
                # Convert to RGB buffer with stride
                static_data = create_rgb_buffer_with_stride(resized_image)
                if static_data is None:
                    print("Using animated test pattern instead")
                    use_static_image = False
                else:
                    use_static_image = True
    else:
        print("Using animated test pattern")
        use_static_image = False
    
    print(f"Refresh rate: {fps} FPS")
    print("Press Ctrl+C to stop")
    
    # Main refresh loop
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            frame_start = time.time()
            
            if continuous_capture:
                # Capture screen continuously
                image = capture_screen()
                if image is not None:
                    # Resize to projector resolution
                    resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
                    if resized_image is not None:
                        # Convert to RGB buffer with stride (quiet mode for continuous capture)
                        data = create_rgb_buffer_with_stride(resized_image, verbose=False)
                    else:
                        data = None
                else:
                    data = None
                    
                if data:
                    # Write to file (quiet mode for continuous capture)
                    if write_to_file(data, verbose=False):
                        frame_count += 1
                        
                        # Calculate and display stats every 10 frames
                        if frame_count % 10 == 0:
                            elapsed = time.time() - start_time
                            actual_fps = frame_count / elapsed if elapsed > 0 else 0
                            print(f"Frame {frame_count} | FPS: {actual_fps:.1f} | Time: {elapsed:.1f}s | Screen: {image.size[0]}x{image.size[1]}")
                else:
                    print("⚠️  Screen capture failed, skipping frame")
                    
            elif use_static_image:
                # Use static image
                data = static_data
                if data:
                    # Write to file
                    if write_to_file(data):
                        frame_count += 1
                        
                        # Calculate and display stats every 10 frames
                        if frame_count % 10 == 0:
                            elapsed = time.time() - start_time
                            actual_fps = frame_count / elapsed if elapsed > 0 else 0
                            print(f"Frame {frame_count} | FPS: {actual_fps:.1f} | Time: {elapsed:.1f}s")
            else:
                # Create animated test pattern
                data = create_test_pattern(frame_count)
                if data:
                    # Write to file
                    if write_to_file(data):
                        frame_count += 1
                        
                        # Calculate and display stats every 10 frames
                        if frame_count % 10 == 0:
                            elapsed = time.time() - start_time
                            actual_fps = frame_count / elapsed if elapsed > 0 else 0
                            print(f"Frame {frame_count} | FPS: {actual_fps:.1f} | Time: {elapsed:.1f}s")
            
            # Calculate sleep time to maintain FPS
            frame_time = time.time() - frame_start
            sleep_time = max(0, frame_interval - frame_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nStopping image display")
        try:
            os.remove("/tmp/temp_screen.jpg")
            os.remove("/tmp/gm12u320_image.rgb")
            if continuous_capture:
                print("Live capture stopped, projector will show test pattern")
            else:
                print("Image files removed, projector will show test pattern")
        except:
            pass
        
        # Final stats
        total_time = time.time() - start_time
        final_fps = frame_count / total_time if total_time > 0 else 0
        print(f"Final stats: {frame_count} frames in {total_time:.1f}s = {final_fps:.1f} FPS")
        if continuous_capture:
            print("Live screen capture completed")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 