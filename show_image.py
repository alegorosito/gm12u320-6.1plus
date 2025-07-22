#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Working version based on the test pattern that functions
"""

import numpy as np
import os
import time
import sys

# Projector settings
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600

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
    print("🧪 Test Pattern Generator")
    print("=========================")
    
    # Create test pattern
    print("Creating test pattern...")
    data = create_test_pattern()
    
    if not data:
        print("❌ Failed to create test pattern")
        return 1
    
    # Write to file
    if not write_to_file(data):
        print("❌ Failed to write test pattern")
        return 1
    
    print("\n🎯 Test pattern created!")
    print("   Should show a gradient from left to right and top to bottom")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping test")
        try:
            os.remove("/tmp/gm12u320_image.rgb")
            print("✅ Test file removed")
        except:
            pass
        return 0

if __name__ == "__main__":
    sys.exit(main()) 