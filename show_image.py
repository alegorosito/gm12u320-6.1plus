#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Simplified version that works with the projector
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
        # Calculate aspect ratio
        img_width, img_height = image.size
        aspect_ratio = img_width / img_height
        target_aspect_ratio = target_width / target_height
        
        if aspect_ratio > target_aspect_ratio:
            # Image is wider than target, fit to width
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            # Image is taller than target, fit to height
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
        
        # Resize image maintaining aspect ratio
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create new image with target size and black background
        new_image = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        
        # Center the resized image
        x = (target_width - new_width) // 2
        y = (target_height - new_height) // 2
        new_image.paste(resized_image, (x, y))
        
        print(f"✅ Image resized from {img_width}x{img_height} to {target_width}x{target_height}")
        print(f"   Resized to {new_width}x{new_height} and centered")
        return new_image
    except Exception as e:
        print(f"❌ Error resizing image: {e}")
        return None

def image_to_rgb_array(image):
    """Convert PIL image to RGB byte array - simplified version"""
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        array = np.array(image, dtype=np.uint8)
        
        # Ensure the array is in the correct shape and format
        if len(array.shape) != 3 or array.shape[2] != 3:
            print(f"❌ Invalid image format: shape={array.shape}")
            return None
        
        # Simple conversion to bytes - no padding, no stride
        rgb_bytes = array.tobytes()
        
        print(f"✅ Image converted to RGB bytes: {len(rgb_bytes)} bytes")
        print(f"   Image shape: {array.shape}")
        print(f"   Expected bytes: {array.shape[0] * array.shape[1] * 3}")
        return rgb_bytes
    except Exception as e:
        print(f"❌ Error converting image to RGB: {e}")
        return None

def write_image_to_file(rgb_bytes, filename="/tmp/gm12u320_image.rgb"):
    """Write RGB bytes to shared file for driver to read"""
    try:
        with open(filename, 'wb') as f:
            f.write(rgb_bytes)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        print(f"✅ Image written to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error writing image to file: {e}")
        return False

def check_projector_status():
    """Check projector device status"""
    print("🎥 GM12U320 Projector Status Checker")
    print("=====================================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("❌ Projector device /dev/dri/card2 not found")
        print("Please make sure the GM12U320 driver is loaded")
        return False
    
    print("✅ Projector device found: /dev/dri/card2")
    return True

def create_simple_test_image():
    """Create a simple test image with solid colors for debugging"""
    try:
        # Create image array using numpy for better control
        image_array = np.zeros((PROJECTOR_HEIGHT, PROJECTOR_WIDTH, 3), dtype=np.uint8)
        
        # Create a debug pattern with specific colors
        # Top third: Pure RED (255, 0, 0)
        image_array[0:PROJECTOR_HEIGHT//3, :, 0] = 255  # Red channel
        image_array[0:PROJECTOR_HEIGHT//3, :, 1] = 0    # Green channel
        image_array[0:PROJECTOR_HEIGHT//3, :, 2] = 0    # Blue channel
        
        # Middle third: Pure GREEN (0, 255, 0)
        image_array[PROJECTOR_HEIGHT//3:2*PROJECTOR_HEIGHT//3, :, 0] = 0    # Red channel
        image_array[PROJECTOR_HEIGHT//3:2*PROJECTOR_HEIGHT//3, :, 1] = 255  # Green channel
        image_array[PROJECTOR_HEIGHT//3:2*PROJECTOR_HEIGHT//3, :, 2] = 0    # Blue channel
        
        # Bottom third: Pure BLUE (0, 0, 255)
        image_array[2*PROJECTOR_HEIGHT//3:, :, 0] = 0    # Red channel
        image_array[2*PROJECTOR_HEIGHT//3:, :, 1] = 0    # Green channel
        image_array[2*PROJECTOR_HEIGHT//3:, :, 2] = 255  # Blue channel
        
        # Convert numpy array to PIL Image
        image = Image.fromarray(image_array, 'RGB')
        
        print("✅ Simple test image created with RGB stripes")
        return image
    except Exception as e:
        print(f"❌ Error creating simple test image: {e}")
        return None

def main():
    """Main function"""
    print("🎥 GM12U320 Projector Image Display")
    print("====================================")
    
    # Check projector status first
    if not check_projector_status():
        return 1
    
    # Get image source from command line or use default
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
            print("   Use a local file path or URL starting with http:// or https://")
            image = None
            
        if image is None:
            print("⚠️  Using simple test image instead")
            image = create_simple_test_image()
    else:
        print("🎯 Creating simple test image")
        image = create_simple_test_image()
    
    if image is None:
        print("❌ Failed to create image")
        return 1
    
    # Resize image
    resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
    if resized_image is None:
        print("❌ Failed to resize image")
        return 1
    
    # Convert to RGB bytes
    rgb_bytes = image_to_rgb_array(resized_image)
    if rgb_bytes is None:
        print("❌ Failed to convert image to RGB")
        return 1
    
    # Write image to shared file for driver to read
    if not write_image_to_file(rgb_bytes):
        print("❌ Failed to write image to shared file")
        return 1
    
    print("\n🎯 Image sent to projector!")
    print("   The driver will read the image from /tmp/gm12u320_image.rgb")
    print("   The projector should now display your image")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            # Keep the script running to maintain the image file
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping image display")
        # Remove the image file to revert to test pattern
        try:
            os.remove("/tmp/gm12u320_image.rgb")
            print("✅ Image file removed, projector will show test pattern")
        except:
            pass
        return 0

if __name__ == "__main__":
    sys.exit(main())