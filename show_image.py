#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Working version based on the test pattern that functions
"""

import numpy as np
import os
import time
import sys
from PIL import Image
import requests
import io

# Projector settings
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600

def load_image_from_path(image_path):
    """Load image from local file path"""
    try:
        print(f"📂 Loading image from: {image_path}")
        image = Image.open(image_path)
        print(f"✅ Image loaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None

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
        # Simple resize to target size
        resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        print(f"✅ Image resized to: {target_width}x{target_height}")
        return resized_image
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
        
        # Simple conversion to bytes
        rgb_bytes = array.tobytes()
        
        print(f"✅ Image converted to RGB bytes: {len(rgb_bytes)} bytes")
        return rgb_bytes
    except Exception as e:
        print(f"❌ Error converting image to RGB: {e}")
        return None

def create_test_pattern():
    """Create a simple test pattern that we know works"""
    # Create a simple array with known values
    image = np.zeros((PROJECTOR_HEIGHT, PROJECTOR_WIDTH, 3), dtype=np.uint8)
    
    # Fill with a simple pattern
    for y in range(PROJECTOR_HEIGHT):
        for x in range(PROJECTOR_WIDTH):
            # Simple gradient pattern
            r = (x * 255) // PROJECTOR_WIDTH
            g = (y * 255) // PROJECTOR_HEIGHT
            b = 128  # Fixed blue value
            
            image[y, x, 0] = r  # Red
            image[y, x, 1] = g  # Green
            image[y, x, 2] = b  # Blue
    
    return image.tobytes()

def write_to_file(data, filename="/tmp/gm12u320_image.rgb"):
    """Write data to file"""
    try:
        with open(filename, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        print(f"✅ Data written to {filename}")
        print(f"   Size: {len(data)} bytes")
        return True
    except Exception as e:
        print(f"❌ Error writing to file: {e}")
        return False

def main():
    print("🎥 GM12U320 Projector Image Display")
    print("====================================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("❌ Projector device /dev/dri/card2 not found")
        print("Please make sure the GM12U320 driver is loaded")
        return 1
    
    print("✅ Projector device found: /dev/dri/card2")
    
    # Get image source from command line or use test pattern
    if len(sys.argv) > 1:
        image_source = sys.argv[1]
        
        # Check if it's a local file or URL
        if os.path.exists(image_source):
            print(f"🎯 Using local image file: {image_source}")
            image = load_image_from_path(image_source)
        elif image_source.startswith(('http://', 'https://')):
            print(f"🎯 Using custom image URL: {image_source}")
            image = download_image(image_source)
        else:
            print(f"❌ Invalid image source: {image_source}")
            image = None
            
        if image is None:
            print("⚠️  Using test pattern instead")
            data = create_test_pattern()
        else:
            # Resize image
            resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized_image is None:
                print("⚠️  Using test pattern instead")
                data = create_test_pattern()
            else:
                # Convert to RGB bytes
                data = image_to_rgb_array(resized_image)
                if data is None:
                    print("⚠️  Using test pattern instead")
                    data = create_test_pattern()
    else:
        print("🎯 Creating test pattern")
        data = create_test_pattern()
    
    if not data:
        print("❌ Failed to create image data")
        return 1
    
    # Write to file
    if not write_to_file(data):
        print("❌ Failed to write image to file")
        return 1
    
    print("\n🎯 Image sent to projector!")
    print("   The driver will read the image from /tmp/gm12u320_image.rgb")
    print("   The projector should now display your image")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping image display")
        try:
            os.remove("/tmp/gm12u320_image.rgb")
            print("✅ Image file removed, projector will show test pattern")
        except:
            pass
        return 0

if __name__ == "__main__":
    sys.exit(main()) 