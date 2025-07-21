#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Downloads an image from URL and displays it on the projector
"""

import requests
import numpy as np
from PIL import Image
import io
import time
import sys
import os

# Projector settings
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
PROJECTOR_BYTES_PER_PIXEL = 3  # RGB

def download_image(url):
    """Download image from URL"""
    try:
        print(f"📥 Downloading image from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(response.content))
        print(f"✅ Image downloaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"❌ Error downloading image: {e}")
        return None

def resize_image(image, target_width, target_height):
    """Resize image to projector resolution"""
    try:
        # Resize image maintaining aspect ratio
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Create new image with target size and black background
        new_image = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        
        # Center the resized image
        x = (target_width - image.size[0]) // 2
        y = (target_height - image.size[1]) // 2
        new_image.paste(image, (x, y))
        
        print(f"✅ Image resized to: {new_image.size[0]}x{new_image.size[1]} pixels")
        return new_image
    except Exception as e:
        print(f"❌ Error resizing image: {e}")
        return None

def image_to_rgb_array(image):
    """Convert PIL image to RGB byte array"""
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        array = np.array(image, dtype=np.uint8)
        
        # Flatten to byte array
        rgb_bytes = array.tobytes()
        
        print(f"✅ Image converted to RGB bytes: {len(rgb_bytes)} bytes")
        return rgb_bytes
    except Exception as e:
        print(f"❌ Error converting image to RGB: {e}")
        return None

def write_to_projector(rgb_bytes):
    """Write RGB bytes to projector device"""
    try:
        # Write to projector device
        with open('/dev/dri/card2', 'wb') as f:
            f.write(rgb_bytes)
            f.flush()
        print("✅ Image sent to projector")
        return True
    except Exception as e:
        print(f"❌ Error writing to projector: {e}")
        return False

def create_test_pattern():
    """Create a test pattern as fallback"""
    try:
        # Create a simple test pattern
        pattern = np.zeros((PROJECTOR_HEIGHT, PROJECTOR_WIDTH, 3), dtype=np.uint8)
        
        # Create a gradient pattern
        for y in range(PROJECTOR_HEIGHT):
            for x in range(PROJECTOR_WIDTH):
                r = (x * 255) // PROJECTOR_WIDTH
                g = (y * 255) // PROJECTOR_HEIGHT
                b = ((x + y) * 255) // (PROJECTOR_WIDTH + PROJECTOR_HEIGHT)
                pattern[y, x] = [r, g, b]
        
        return pattern.tobytes()
    except Exception as e:
        print(f"❌ Error creating test pattern: {e}")
        return None

def main():
    """Main function"""
    print("🎥 GM12U320 Projector Image Display")
    print("====================================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("❌ Projector device /dev/dri/card2 not found")
        print("Please make sure the GM12U320 driver is loaded")
        return 1
    
    print("✅ Projector device found")
    
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "https://picsum.photos/id/1/200/300"
    
    # Download and process image
    image = download_image(url)
    if image is None:
        print("⚠️  Using test pattern instead")
        rgb_bytes = create_test_pattern()
    else:
        # Resize image
        resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
        if resized_image is None:
            print("⚠️  Using test pattern instead")
            rgb_bytes = create_test_pattern()
        else:
            # Convert to RGB bytes
            rgb_bytes = image_to_rgb_array(resized_image)
            if rgb_bytes is None:
                print("⚠️  Using test pattern instead")
                rgb_bytes = create_test_pattern()
    
    if rgb_bytes is None:
        print("❌ Failed to create image data")
        return 1
    
    # Display image on projector
    print("🔄 Displaying image on projector...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            if write_to_projector(rgb_bytes):
                time.sleep(0.1)  # 10 FPS
            else:
                time.sleep(1)  # Wait longer on error
    except KeyboardInterrupt:
        print("\n🛑 Stopping image display")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 