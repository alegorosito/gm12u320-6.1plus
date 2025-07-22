#!/usr/bin/env python3
"""
GM12U320 Simple Live Screen Mirror
Uses basic Python libraries to capture screen and update projector
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
CAPTURE_INTERVAL = 0.2  # 200ms (slower but more compatible)

class SimpleMirror:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.last_capture_time = 0
        
    def check_dependencies(self):
        """Check if required dependencies are available"""
        if not os.path.exists('/dev/dri/card2'):
            print("❌ Projector device /dev/dri/card2 not found")
            print("Please make sure the GM12U320 driver is loaded")
            return False
            
        # Check if we can capture screen
        try:
            # Try to use importlib to check if mss is available
            import importlib.util
            if importlib.util.find_spec("mss") is not None:
                print("✅ mss library available - using fast capture")
                return "mss"
            else:
                print("⚠️  mss not available - using alternative method")
                return "alternative"
        except:
            print("⚠️  mss not available - using alternative method")
            return "alternative"
    
    def capture_screen_mss(self):
        """Capture screen using mss (fast method)"""
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]  # Primary monitor
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                return img
        except Exception as e:
            print(f"Error with mss capture: {e}")
            return None
    
    def capture_screen_alternative(self):
        """Capture screen using alternative method (slower but works everywhere)"""
        try:
            # Try using xdg-desktop-portal or similar
            # For now, create a test pattern that changes
            return self.create_dynamic_test_pattern()
        except Exception as e:
            print(f"Error with alternative capture: {e}")
            return None
    
    def create_dynamic_test_pattern(self):
        """Create a dynamic test pattern that simulates screen changes"""
        try:
            # Create a pattern that changes over time
            current_time = int(time.time() * 10)  # Change every 100ms
            
            image = Image.new('RGB', (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), (0, 0, 0))
            
            # Create moving elements
            for i in range(10):
                x = (current_time + i * 50) % PROJECTOR_WIDTH
                y = (current_time + i * 30) % PROJECTOR_HEIGHT
                
                # Draw a moving circle
                for dy in range(-20, 21):
                    for dx in range(-20, 21):
                        if dx*dx + dy*dy <= 400:  # Circle radius 20
                            px, py = x + dx, y + dy
                            if 0 <= px < PROJECTOR_WIDTH and 0 <= py < PROJECTOR_HEIGHT:
                                r = (current_time + i * 25) % 256
                                g = (current_time + i * 50) % 256
                                b = (current_time + i * 75) % 256
                                image.putpixel((px, py), (r, g, b))
            
            # Add text showing it's a test pattern
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
                except:
                    font = ImageFont.load_default()
                
                text = f"LIVE TEST {current_time}"
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
            
            # Validate file size
            file_size = os.path.getsize(filename)
            
            if file_size == TOTAL_FILE_SIZE:
                return True
            else:
                print(f"File size validation: FAILED (expected {TOTAL_FILE_SIZE}, got {file_size})")
                return False
                
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False
    
    def update_projector(self, capture_method):
        """Capture screen and update projector"""
        try:
            # Capture screen
            if capture_method == "mss":
                screenshot = self.capture_screen_mss()
            else:
                screenshot = self.capture_screen_alternative()
                
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
    
    def mirror_loop(self, capture_method):
        """Main mirroring loop"""
        print("Starting simple live mirror...")
        print(f"Capture interval: {CAPTURE_INTERVAL*1000:.0f}ms")
        print(f"Capture method: {capture_method}")
        print(f"Target resolution: {PROJECTOR_WIDTH}x{PROJECTOR_HEIGHT}")
        print("Press Ctrl+C to stop")
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check if it's time for next capture
                if current_time - self.last_capture_time >= CAPTURE_INTERVAL:
                    success = self.update_projector(capture_method)
                    self.last_capture_time = current_time
                    
                    if success:
                        elapsed = current_time - start_time
                        fps = self.frame_count / elapsed if elapsed > 0 else 0
                        print(f"\rFrames: {self.frame_count} | FPS: {fps:.1f} | Time: {elapsed:.1f}s | Method: {capture_method}", end="", flush=True)
                    else:
                        print(f"\rFrame {self.frame_count} failed", end="", flush=True)
                
                # Small sleep to prevent CPU overload
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nStopping simple mirror...")
        finally:
            self.running = False
    
    def start(self):
        """Start the simple mirror"""
        capture_method = self.check_dependencies()
        if not capture_method:
            return False
        
        print("GM12U320 Simple Live Mirror")
        print("===========================")
        print("This will show live content on the projector")
        if capture_method == "alternative":
            print("Using dynamic test pattern (no real screen capture)")
        else:
            print("Using real screen capture")
        print("Press Ctrl+C to stop")
        
        try:
            self.mirror_loop(capture_method)
        except Exception as e:
            print(f"Error in mirror loop: {e}")
        finally:
            # Cleanup
            try:
                os.remove("/tmp/gm12u320_image.rgb")
                print("Cleanup complete")
            except:
                pass
        
        return True

def main():
    mirror = SimpleMirror()
    return 0 if mirror.start() else 1

if __name__ == "__main__":
    sys.exit(main()) 