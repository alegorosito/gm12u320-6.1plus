#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Downloads an image from URL and displays it on the projector
"""

import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import time
import sys
import os

# Projector settings
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
PROJECTOR_BYTES_PER_PIXEL = 3  # RGB

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

def create_simple_test_image():
    """Create a simple test image with solid colors for debugging"""
    try:
        # Create image array using numpy for better control
        image_array = np.zeros((PROJECTOR_HEIGHT, PROJECTOR_WIDTH, 3), dtype=np.uint8)
        
        # Create a simple pattern: red, green, blue stripes
        stripe_height = PROJECTOR_HEIGHT // 3
        
        # Red stripe (top) - will become blue in BGR
        image_array[0:stripe_height, :, 0] = 255  # Red channel
        image_array[0:stripe_height, :, 1] = 0    # Green channel
        image_array[0:stripe_height, :, 2] = 0    # Blue channel
        
        # Green stripe (middle) - stays green in BGR
        image_array[stripe_height:2*stripe_height, :, 0] = 0    # Red channel
        image_array[stripe_height:2*stripe_height, :, 1] = 255  # Green channel
        image_array[stripe_height:2*stripe_height, :, 2] = 0    # Blue channel
        
        # Blue stripe (bottom) - will become red in BGR
        image_array[2*stripe_height:, :, 0] = 0    # Red channel
        image_array[2*stripe_height:, :, 1] = 0    # Green channel
        image_array[2*stripe_height:, :, 2] = 255  # Blue channel
        
        # Add a white border
        border_width = 20
        image_array[0:border_width, :, :] = 255  # Top border
        image_array[-border_width:, :, :] = 255  # Bottom border
        image_array[:, 0:border_width, :] = 255  # Left border
        image_array[:, -border_width:, :] = 255  # Right border
        
        # Convert numpy array to PIL Image
        image = Image.fromarray(image_array, 'RGB')
        
        print("✅ Simple test image created with RGB stripes (will be converted to BGR)")
        return image
    except Exception as e:
        print(f"❌ Error creating simple test image: {e}")
        return None

def create_text_image(text="GM12U320 Projector", subtitle="Image Display Test"):
    """Create a text-based image that's easy to read"""
    try:
        # Create a new image with white background
        image = Image.new('RGB', (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Try to use a system font, fallback to default
        try:
            # Try different font sizes and names
            font_sizes = [48, 36, 24]
            font_names = ['Arial', 'DejaVuSans', 'LiberationSans', 'FreeSans']
            
            font = None
            for font_name in font_names:
                for font_size in font_sizes:
                    try:
                        font = ImageFont.truetype(font_name, font_size)
                        break
                    except:
                        continue
                if font:
                    break
            
            if not font:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Calculate text positions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (PROJECTOR_WIDTH - text_width) // 2
        y = (PROJECTOR_HEIGHT - text_height) // 2 - 50
        
        # Draw main text
        draw.text((x, y), text, fill=(0, 0, 0), font=font)
        
        # Draw subtitle
        bbox_sub = draw.textbbox((0, 0), subtitle, font=font)
        sub_width = bbox_sub[2] - bbox_sub[0]
        x_sub = (PROJECTOR_WIDTH - sub_width) // 2
        y_sub = y + text_height + 20
        
        draw.text((x_sub, y_sub), subtitle, fill=(100, 100, 100), font=font)
        
        # Add a border
        draw.rectangle([10, 10, PROJECTOR_WIDTH-10, PROJECTOR_HEIGHT-10], outline=(0, 0, 255), width=3)
        
        print(f"✅ Text image created: {text}")
        return image
    except Exception as e:
        print(f"❌ Error creating text image: {e}")
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
    """
    Convert PIL image to properly aligned byte array for GM12U320 projector.
    Ensures it’s in BGR format if required.
    """
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        array = np.array(image, dtype=np.uint8)

        # Si el proyector espera BGR, descomenta la siguiente línea:
        array = array[:, :, ::-1]

        # Por seguridad, asegúrate de que no hay padding en las filas.
        # Si el driver espera que cada fila sea múltiplo de 4 bytes:
        h, w, c = array.shape
        row_size = w * c
        pad = (4 - (row_size % 4)) % 4
        
        if pad != 0:
            padded = np.zeros((h, w*c + pad), dtype=np.uint8)
            for y in range(h):
                padded[y, :row_size] = array[y].flatten()
            print(f"✅ Image padded: {pad} bytes per row to align")
            return padded.tobytes()
        else:
            print("✅ Image has correct row size, no padding needed")
            return array.tobytes()
        
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
    
    # Check device permissions
    try:
        stat_info = os.stat('/dev/dri/card2')
        print(f"📊 Device permissions: {oct(stat_info.st_mode)[-3:]}")
        print(f"👤 Owner: {stat_info.st_uid}")
        print(f"👥 Group: {stat_info.st_gid}")
    except Exception as e:
        print(f"❌ Error getting device info: {e}")
    
    # Check sysfs information
    sysfs_path = '/sys/class/drm/card2'
    if os.path.exists(sysfs_path):
        print(f"📁 Sysfs path exists: {sysfs_path}")
        
        # Check device status
        status_path = os.path.join(sysfs_path, 'card2-Unknown-1/status')
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r') as f:
                    status = f.read().strip()
                print(f"📊 Device status: {status}")
            except Exception as e:
                print(f"❌ Error reading status: {e}")
    else:
        print(f"❌ Sysfs path not found: {sysfs_path}")
    
    return True

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