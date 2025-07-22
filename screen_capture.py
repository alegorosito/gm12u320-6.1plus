#!/usr/bin/env python3
"""
Simple Screen Capture Script
Captures screen every 200ms and saves as JPEG
"""

import os
import sys
import time
import subprocess
from PIL import Image

# Capture settings
CAPTURE_INTERVAL = 0.2  # 200ms
OUTPUT_FILE = "/tmp/ubuntu_screen.jpg"
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768

class ScreenCapture:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        
    def capture_screen(self):
        """Capture screen using multiple methods"""
        try:
            # Method 1: Direct framebuffer read
            try:
                with open('/dev/fb0', 'rb') as fb:
                    fb.seek(0)
                    data = fb.read(SCREEN_WIDTH * SCREEN_HEIGHT * 3)
                    
                    if len(data) >= SCREEN_WIDTH * SCREEN_HEIGHT * 3:
                        img = Image.frombytes('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), 
                                            data[:SCREEN_WIDTH * SCREEN_HEIGHT * 3])
                        print(f"✅ Captured {SCREEN_WIDTH}x{SCREEN_HEIGHT} from framebuffer")
                        return img
                    else:
                        print(f"❌ Insufficient framebuffer data: {len(data)} bytes")
            except Exception as e:
                print(f"Framebuffer capture failed: {e}")
            
            # Method 2: Try import command (ImageMagick)
            try:
                result = subprocess.run(['import', '-window', 'root', '-resize', 
                                       f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}', OUTPUT_FILE], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0 and os.path.exists(OUTPUT_FILE):
                    img = Image.open(OUTPUT_FILE)
                    print("✅ Captured using import command")
                    return img
            except Exception as e:
                print(f"Import command failed: {e}")
            
            # Method 3: Try xwd command
            try:
                result = subprocess.run(['xwd', '-root', '-out', '/tmp/temp_screen.xwd'], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0 and os.path.exists('/tmp/temp_screen.xwd'):
                    # Convert xwd to jpg
                    subprocess.run(['convert', '/tmp/temp_screen.xwd', OUTPUT_FILE], 
                                 capture_output=True, timeout=5)
                    if os.path.exists(OUTPUT_FILE):
                        img = Image.open(OUTPUT_FILE)
                        os.remove('/tmp/temp_screen.xwd')
                        print("✅ Captured using xwd command")
                        return img
            except Exception as e:
                print(f"Xwd command failed: {e}")
            
            # Method 4: Create test pattern
            print("⚠️ Using test pattern as fallback")
            return self.create_test_pattern()
            
        except Exception as e:
            print(f"❌ Screen capture error: {e}")
            return None
    
    def create_test_pattern(self):
        """Create a test pattern"""
        try:
            current_time = int(time.time() * 10)
            
            image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
            
            # Draw some moving elements
            for i in range(5):
                x = (current_time + i * 100) % SCREEN_WIDTH
                y = (current_time + i * 50) % SCREEN_HEIGHT
                
                # Draw a rectangle
                for dy in range(-30, 31):
                    for dx in range(-30, 31):
                        px, py = x + dx, y + dy
                        if 0 <= px < SCREEN_WIDTH and 0 <= py < SCREEN_HEIGHT:
                            r = (current_time + i * 50) % 256
                            g = (current_time + i * 100) % 256
                            b = (current_time + i * 150) % 256
                            image.putpixel((px, py), (r, g, b))
            
            # Add text
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                except:
                    font = ImageFont.load_default()
                
                text = f"SCREEN CAPTURE TEST {current_time}"
                draw.text((50, 50), text, fill=(255, 255, 255), font=font)
                
                text2 = f"Frame: {self.frame_count} | Time: {time.strftime('%H:%M:%S')}"
                draw.text((50, 100), text2, fill=(200, 200, 200), font=font)
            except:
                pass
            
            return image
        except Exception as e:
            print(f"Error creating test pattern: {e}")
            return None
    
    def save_image(self, image):
        """Save image as JPEG"""
        try:
            image.save(OUTPUT_FILE, 'JPEG', quality=85)
            file_size = os.path.getsize(OUTPUT_FILE)
            print(f"💾 Saved to {OUTPUT_FILE} ({file_size} bytes)")
            return True
        except Exception as e:
            print(f"❌ Error saving image: {e}")
            return False
    
    def capture_loop(self):
        """Main capture loop"""
        print("📸 Starting screen capture...")
        print(f"📁 Output file: {OUTPUT_FILE}")
        print(f"⏱️  Capture interval: {CAPTURE_INTERVAL*1000:.0f}ms")
        print(f"🖥️  Screen resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        print("Press Ctrl+C to stop")
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Capture screen
                print(f"\n🔄 Frame {self.frame_count + 1}: Capturing...")
                image = self.capture_screen()
                
                if image is not None:
                    # Save image
                    if self.save_image(image):
                        self.frame_count += 1
                        elapsed = current_time - start_time
                        fps = self.frame_count / elapsed if elapsed > 0 else 0
                        print(f"✅ Frame {self.frame_count} saved | FPS: {fps:.1f} | Time: {elapsed:.1f}s")
                    else:
                        print(f"❌ Failed to save frame {self.frame_count + 1}")
                else:
                    print(f"❌ Failed to capture frame {self.frame_count + 1}")
                
                # Wait for next capture
                time.sleep(CAPTURE_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping screen capture...")
        finally:
            self.running = False
    
    def start(self):
        """Start the screen capture"""
        print("Screen Capture Tool")
        print("===================")
        print("This will capture your screen every 200ms")
        print("and save it as a JPEG file")
        print("Press Ctrl+C to stop")
        
        try:
            self.capture_loop()
        except Exception as e:
            print(f"Error in capture loop: {e}")
        finally:
            print(f"\n📊 Capture complete!")
            print(f"Total frames captured: {self.frame_count}")
            print(f"Final file: {OUTPUT_FILE}")
        
        return True

def main():
    capture = ScreenCapture()
    return 0 if capture.start() else 1

if __name__ == "__main__":
    sys.exit(main()) 