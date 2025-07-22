#!/usr/bin/env python3
"""
Ubuntu Screen Capture Script
Works with Ubuntu graphical interface
"""

import os
import sys
import time
import subprocess
import numpy as np
from PIL import Image

# Capture settings
CAPTURE_INTERVAL = 0.2  # 200ms
OUTPUT_FILE = "/tmp/ubuntu_screen.jpg"

class UbuntuCapture:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        
    def check_environment(self):
        """Check Ubuntu environment"""
        print("🔍 Checking Ubuntu environment...")
        
        # Check if we're in a graphical environment
        if os.environ.get('DISPLAY'):
            print(f"✅ DISPLAY set: {os.environ.get('DISPLAY')}")
        else:
            print("❌ No DISPLAY environment variable")
            return False
        
        # Check if we're running as root
        if os.geteuid() == 0:
            print("⚠️ Running as root - this might cause issues")
        else:
            print("✅ Running as regular user")
        
        # Check available capture tools
        tools = ['gnome-screenshot', 'import', 'xwd', 'ffmpeg']
        available_tools = []
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool], capture_output=True, text=True)
                if result.returncode == 0:
                    available_tools.append(tool)
                    print(f"✅ {tool} available")
                else:
                    print(f"❌ {tool} not found")
            except:
                print(f"❌ {tool} not found")
        
        if not available_tools:
            print("❌ No capture tools available")
            return False
        
        print(f"📋 Available tools: {available_tools}")
        return True
    
    def capture_with_gnome_screenshot(self):
        """Capture using gnome-screenshot"""
        try:
            print("📸 Trying gnome-screenshot...")
            result = subprocess.run(['gnome-screenshot', '-f', OUTPUT_FILE, '--no-border'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0 and os.path.exists(OUTPUT_FILE):
                img = Image.open(OUTPUT_FILE)
                print(f"✅ gnome-screenshot captured: {img.size[0]}x{img.size[1]}")
                return img
            else:
                print(f"❌ gnome-screenshot failed: {result.stderr.decode()}")
        except Exception as e:
            print(f"❌ gnome-screenshot error: {e}")
        return None
    
    def capture_with_import(self):
        """Capture using ImageMagick import"""
        try:
            print("📸 Trying import command...")
            result = subprocess.run(['import', '-window', 'root', OUTPUT_FILE], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0 and os.path.exists(OUTPUT_FILE):
                img = Image.open(OUTPUT_FILE)
                print(f"✅ import captured: {img.size[0]}x{img.size[1]}")
                return img
            else:
                print(f"❌ import failed: {result.stderr.decode()}")
        except Exception as e:
            print(f"❌ import error: {e}")
        return None
    
    def capture_with_xwd(self):
        """Capture using xwd"""
        try:
            print("📸 Trying xwd command...")
            result = subprocess.run(['xwd', '-root', '-out', '/tmp/temp_screen.xwd'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0 and os.path.exists('/tmp/temp_screen.xwd'):
                # Convert xwd to jpg
                convert_result = subprocess.run(['convert', '/tmp/temp_screen.xwd', OUTPUT_FILE], 
                                             capture_output=True, timeout=5)
                if convert_result.returncode == 0 and os.path.exists(OUTPUT_FILE):
                    img = Image.open(OUTPUT_FILE)
                    os.remove('/tmp/temp_screen.xwd')
                    print(f"✅ xwd captured: {img.size[0]}x{img.size[1]}")
                    return img
                else:
                    print(f"❌ convert failed: {convert_result.stderr.decode()}")
            else:
                print(f"❌ xwd failed: {result.stderr.decode()}")
        except Exception as e:
            print(f"❌ xwd error: {e}")
        return None
    
    def capture_with_ffmpeg(self):
        """Capture using ffmpeg"""
        try:
            print("📸 Trying ffmpeg...")
            cmd = [
                'ffmpeg', '-f', 'x11grab', '-i', ':0.0', '-vframes', '1',
                '-y', OUTPUT_FILE
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0 and os.path.exists(OUTPUT_FILE):
                img = Image.open(OUTPUT_FILE)
                print(f"✅ ffmpeg captured: {img.size[0]}x{img.size[1]}")
                return img
            else:
                print(f"❌ ffmpeg failed: {result.stderr.decode()}")
        except Exception as e:
            print(f"❌ ffmpeg error: {e}")
        return None
    
    def capture_screen(self):
        """Capture screen using best available method"""
        # Try methods in order of preference
        methods = [
            ('gnome-screenshot', self.capture_with_gnome_screenshot),
            ('import', self.capture_with_import),
            ('xwd', self.capture_with_xwd),
            ('ffmpeg', self.capture_with_ffmpeg)
        ]
        
        for method_name, method_func in methods:
            try:
                img = method_func()
                if img is not None:
                    return img
            except Exception as e:
                print(f"❌ {method_name} method failed: {e}")
        
        print("❌ All capture methods failed")
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
        print("📸 Starting Ubuntu screen capture...")
        print(f"📁 Output file: {OUTPUT_FILE}")
        print(f"⏱️  Capture interval: {CAPTURE_INTERVAL*1000:.0f}ms")
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
        print("Ubuntu Screen Capture Tool")
        print("=========================")
        print("This will capture your Ubuntu screen every 200ms")
        print("and save it as a JPEG file")
        print("Press Ctrl+C to stop")
        
        if not self.check_environment():
            print("❌ Environment check failed")
            return False
        
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
    capture = UbuntuCapture()
    return 0 if capture.start() else 1

if __name__ == "__main__":
    sys.exit(main()) 