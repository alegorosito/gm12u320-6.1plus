#!/usr/bin/env python3
"""
GM12U320 Smart Screen Mirror
Automatically detects and captures the active screen
"""

import numpy as np
import os
import sys
import time
import subprocess
from PIL import Image

# Projector specifications (optimized)
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
BYTES_PER_PIXEL = 3
DATA_BYTES_PER_LINE = PROJECTOR_WIDTH * BYTES_PER_PIXEL  # 2400 bytes
STRIDE_BYTES_PER_LINE = 2562  # 2400 data + 162 padding
PADDING_BYTES_PER_LINE = STRIDE_BYTES_PER_LINE - DATA_BYTES_PER_LINE  # 162 bytes
TOTAL_FILE_SIZE = STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT  # 1,537,200 bytes

# Capture settings
CAPTURE_INTERVAL = 0.2  # 200ms

class SmartMirror:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.last_capture_time = 0
        self.active_framebuffer = None
        
    def check_dependencies(self):
        """Check if required dependencies are available"""
        if not os.path.exists('/dev/dri/card2'):
            print("❌ Projector device /dev/dri/card2 not found")
            print("Please make sure the GM12U320 driver is loaded")
            return False
        print("✅ Projector device found")
        return True
    
    def find_active_framebuffer(self):
        """Find which framebuffer contains active screen content"""
        print("🔍 Searching for active framebuffer...")
        
        # List all framebuffers
        framebuffers = []
        for i in range(4):  # Check fb0 to fb3
            fb_path = f'/dev/fb{i}'
            if os.path.exists(fb_path):
                framebuffers.append(fb_path)
        
        print(f"Found framebuffers: {framebuffers}")
        
        # Test each framebuffer for content
        for fb_path in framebuffers:
            print(f"Testing {fb_path}...")
            try:
                with open(fb_path, 'rb') as fb:
                    # Read a small sample to check if it has content
                    fb.seek(0)
                    sample = fb.read(1024)  # Read 1KB sample
                    
                    if len(sample) > 0:
                        # Check if the sample contains non-zero data
                        if any(b != 0 for b in sample):
                            print(f"✅ {fb_path} contains data")
                            
                            # Try to get framebuffer info
                            try:
                                result = subprocess.run(['fbset', '-fb', fb_path], 
                                                      capture_output=True, text=True, timeout=2)
                                if result.returncode == 0:
                                    print(f"Framebuffer info: {result.stdout}")
                            except:
                                pass
                            
                            return fb_path
                        else:
                            print(f"❌ {fb_path} is empty (all zeros)")
                    else:
                        print(f"❌ {fb_path} is empty")
                        
            except PermissionError:
                print(f"❌ Permission denied accessing {fb_path}")
            except Exception as e:
                print(f"❌ Error testing {fb_path}: {e}")
        
        print("❌ No active framebuffer found")
        return None
    
    def capture_from_framebuffer(self, fb_path):
        """Capture screen from specific framebuffer"""
        try:
            print(f"📺 Capturing from {fb_path}...")
            
            with open(fb_path, 'rb') as fb:
                # Read framebuffer data
                fb.seek(0)
                data = fb.read(PROJECTOR_WIDTH * PROJECTOR_HEIGHT * 3)
                
                if len(data) >= PROJECTOR_WIDTH * PROJECTOR_HEIGHT * 3:
                    # Convert raw data to PIL Image
                    img = Image.frombytes('RGB', (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), 
                                        data[:PROJECTOR_WIDTH * PROJECTOR_HEIGHT * 3])
                    
                    # Check if image has content (not all black)
                    img_array = np.array(img)
                    if np.any(img_array > 0):
                        print(f"✅ Captured {PROJECTOR_WIDTH}x{PROJECTOR_HEIGHT} with content")
                        return img
                    else:
                        print(f"❌ Captured image is all black")
                        return None
                else:
                    print(f"❌ Insufficient data: {len(data)} bytes")
                    return None
                    
        except PermissionError:
            print(f"❌ Permission denied accessing {fb_path}")
            return None
        except Exception as e:
            print(f"❌ Error capturing from {fb_path}: {e}")
            return None
    
    def capture_screen_simple(self):
        """Simple screen capture approach"""
        try:
            print("📸 Taking simple screen capture...")
            
            # Method 1: Try to read framebuffer directly
            try:
                with open('/dev/fb0', 'rb') as fb:
                    fb.seek(0)
                    # Read a reasonable amount of data
                    data = fb.read(1920 * 1080 * 3)  # Common resolution
                    
                    if len(data) > 0:
                        # Try to create image from data
                        # Assume it's 1920x1080 or similar
                        width = 1920
                        height = 1080
                        
                        # Make sure we have enough data
                        if len(data) >= width * height * 3:
                            img = Image.frombytes('RGB', (width, height), data[:width * height * 3])
                            print(f"✅ Captured {width}x{height} from framebuffer")
                            return img
                        else:
                            # Try smaller resolution
                            width = 800
                            height = 600
                            if len(data) >= width * height * 3:
                                img = Image.frombytes('RGB', (width, height), data[:width * height * 3])
                                print(f"✅ Captured {width}x{height} from framebuffer")
                                return img
            except Exception as e:
                print(f"Framebuffer capture failed: {e}")
            
            # Method 2: Try to use import command to capture screen
            try:
                print("Trying import command...")
                result = subprocess.run(['import', '-window', 'root', '-resize', '800x600', 'temp_screen.png'], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0 and os.path.exists('temp_screen.png'):
                    img = Image.open('temp_screen.png')
                    os.remove('temp_screen.png')
                    print("✅ Captured using import command")
                    return img
            except Exception as e:
                print(f"Import command failed: {e}")
            
            # Method 3: Try to use xwd command
            try:
                print("Trying xwd command...")
                result = subprocess.run(['xwd', '-root', '-out', 'temp_screen.xwd'], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0 and os.path.exists('temp_screen.xwd'):
                    # Convert xwd to png using ImageMagick
                    subprocess.run(['convert', 'temp_screen.xwd', 'temp_screen.png'], 
                                 capture_output=True, timeout=5)
                    if os.path.exists('temp_screen.png'):
                        img = Image.open('temp_screen.png')
                        os.remove('temp_screen.xwd')
                        os.remove('temp_screen.png')
                        print("✅ Captured using xwd command")
                        return img
            except Exception as e:
                print(f"Xwd command failed: {e}")
            
            print("❌ All simple capture methods failed")
            return None
            
        except Exception as e:
            print(f"❌ Simple capture error: {e}")
            return None
    
    def create_dynamic_test_pattern(self):
        """Create a dynamic test pattern that simulates screen changes"""
        try:
            current_time = int(time.time() * 10)
            
            image = Image.new('RGB', (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), (0, 0, 0))
            
            # Create moving elements
            for i in range(10):
                x = (current_time + i * 50) % PROJECTOR_WIDTH
                y = (current_time + i * 30) % PROJECTOR_HEIGHT
                
                # Draw a moving circle
                for dy in range(-20, 21):
                    for dx in range(-20, 21):
                        if dx*dx + dy*dy <= 400:
                            px, py = x + dx, y + dy
                            if 0 <= px < PROJECTOR_WIDTH and 0 <= py < PROJECTOR_HEIGHT:
                                r = (current_time + i * 25) % 256
                                g = (current_time + i * 50) % 256
                                b = (current_time + i * 75) % 256
                                image.putpixel((px, py), (r, g, b))
            
            # Add text
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
                except:
                    font = ImageFont.load_default()
                
                text = f"SMART TEST {current_time}"
                draw.text((10, 10), text, fill=(255, 255, 255), font=font)
            except:
                pass
            
            return image
        except Exception as e:
            print(f"Error creating test pattern: {e}")
            return None
    
    def resize_image(self, image, target_width, target_height):
        """Resize image to projector resolution"""
        try:
            resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            return resized_image
        except Exception as e:
            print(f"Error resizing image: {e}")
            return None
    
    def create_rgb_buffer_with_stride(self, image):
        """Convert PIL image to RGB buffer with proper stride and BGR color order"""
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            array = np.array(image, dtype=np.uint8)
            buffer = bytearray()
            
            for y in range(PROJECTOR_HEIGHT):
                for x in range(PROJECTOR_WIDTH):
                    r, g, b = array[y, x]
                    # Use BGR order (test 2 was correct)
                    buffer.extend([b, g, r])
                
                # Add padding bytes to reach stride
                buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
            
            return bytes(buffer)
        except Exception as e:
            print(f"Error creating RGB buffer: {e}")
            return None
    
    def write_to_file(self, data, filename="/tmp/gm12u320_image.rgb"):
        """Write data to file with validation"""
        try:
            with open(filename, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            
            file_size = os.path.getsize(filename)
            
            if file_size == TOTAL_FILE_SIZE:
                return True
            else:
                print(f"File size validation: FAILED (expected {TOTAL_FILE_SIZE}, got {file_size})")
                return False
                
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False
    
    def update_projector(self):
        """Capture screen and update projector"""
        try:
            screenshot = None
            
            # Try simple capture methods
            screenshot = self.capture_screen_simple()
            
            # Fallback to test pattern if all methods fail
            if screenshot is None:
                print("Using test pattern as fallback")
                screenshot = self.create_dynamic_test_pattern()
            
            if screenshot is None:
                return False
            
            # Resize to projector resolution
            resized = self.resize_image(screenshot, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized is None:
                return False
            
            # Convert to RGB buffer
            buffer = self.create_rgb_buffer_with_stride(resized)
            if buffer is None:
                return False
            
            # Write to file
            if not self.write_to_file(buffer):
                return False
            
            self.frame_count += 1
            return True
            
        except Exception as e:
            print(f"Error updating projector: {e}")
            return False
    
    def mirror_loop(self):
        """Main mirroring loop"""
        print("Starting simple live mirror...")
        print(f"Capture interval: {CAPTURE_INTERVAL*1000:.0f}ms")
        print(f"Target resolution: {PROJECTOR_WIDTH}x{PROJECTOR_HEIGHT}")
        print("Press Ctrl+C to stop")
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                if current_time - self.last_capture_time >= CAPTURE_INTERVAL:
                    success = self.update_projector()
                    self.last_capture_time = current_time
                    
                    if success:
                        elapsed = current_time - start_time
                        fps = self.frame_count / elapsed if elapsed > 0 else 0
                        print(f"\rFrames: {self.frame_count} | FPS: {fps:.1f} | Time: {elapsed:.1f}s", end="", flush=True)
                    else:
                        print(f"\rFrame {self.frame_count} failed", end="", flush=True)
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nStopping smart mirror...")
        finally:
            self.running = False
    
    def start(self):
        """Start the smart mirror"""
        if not self.check_dependencies():
            return False
        
        print("GM12U320 Simple Live Mirror")
        print("===========================")
        print("This will capture screen using simple methods")
        print("Press Ctrl+C to stop")
        
        try:
            self.mirror_loop()
        except Exception as e:
            print(f"Error in mirror loop: {e}")
        finally:
            try:
                os.remove("/tmp/gm12u320_image.rgb")
                print("Cleanup complete")
            except:
                pass
        
        return True

def main():
    mirror = SmartMirror()
    return 0 if mirror.start() else 1

if __name__ == "__main__":
    sys.exit(main()) 