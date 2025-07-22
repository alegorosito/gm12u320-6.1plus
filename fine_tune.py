#!/usr/bin/env python3
"""
GM12U320 Color Calibration Script
Automatically tests different RGB color combinations
"""

import numpy as np
import os
import sys
import time
from PIL import Image, ImageDraw, ImageFont

# Projector specifications (updated stride)
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
BYTES_PER_PIXEL = 3
DATA_BYTES_PER_LINE = PROJECTOR_WIDTH * BYTES_PER_PIXEL  # 2400 bytes
STRIDE_BYTES_PER_LINE = 2562  # 2400 data + 162 padding
PADDING_BYTES_PER_LINE = STRIDE_BYTES_PER_LINE - DATA_BYTES_PER_LINE  # 162 bytes
TOTAL_FILE_SIZE = STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT  # 1,537,200 bytes

def create_color_test_pattern(test_number, r_order, g_order, b_order):
    """Create a test pattern with specific color order and test number"""
    try:
        # Create image with test number
        image = Image.new('RGB', (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Try to use a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 60)
            except:
                font = ImageFont.load_default()
        
        # Draw test number
        test_text = f"TEST {test_number:02d}"
        text_bbox = draw.textbbox((0, 0), test_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (PROJECTOR_WIDTH - text_width) // 2
        y = (PROJECTOR_HEIGHT - text_height) // 2
        
        draw.text((x, y), test_text, fill=(255, 255, 255), font=font)
        
        # Add color order info
        order_text = f"RGB Order: {r_order}{g_order}{b_order}"
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            try:
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 30)
            except:
                small_font = ImageFont.load_default()
        
        order_bbox = draw.textbbox((0, 0), order_text, small_font)
        order_width = order_bbox[2] - order_bbox[0]
        order_x = (PROJECTOR_WIDTH - order_width) // 2
        order_y = y + text_height + 20
        
        draw.text((order_x, order_y), order_text, fill=(200, 200, 200), font=small_font)
        
        # Add color bars at the bottom
        bar_height = 100
        bar_y = PROJECTOR_HEIGHT - bar_height - 50
        
        # Red bar
        draw.rectangle([0, bar_y, PROJECTOR_WIDTH//3, bar_y + bar_height], fill=(255, 0, 0))
        draw.text((10, bar_y + 10), "RED", fill=(255, 255, 255), font=small_font)
        
        # Green bar
        draw.rectangle([PROJECTOR_WIDTH//3, bar_y, 2*PROJECTOR_WIDTH//3, bar_y + bar_height], fill=(0, 255, 0))
        draw.text([PROJECTOR_WIDTH//3 + 10, bar_y + 10], "GREEN", fill=(0, 0, 0), font=small_font)
        
        # Blue bar
        draw.rectangle([2*PROJECTOR_WIDTH//3, bar_y, PROJECTOR_WIDTH, bar_y + bar_height], fill=(0, 0, 255))
        draw.text([2*PROJECTOR_WIDTH//3 + 10, bar_y + 10], "BLUE", fill=(255, 255, 255), font=small_font)
        
        return image
    except Exception as e:
        print(f"Error creating test pattern: {e}")
        return None

def create_rgb_buffer_with_stride(image, r_order, g_order, b_order):
    """Convert PIL image to RGB buffer with custom color order and proper stride"""
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
                
                # Apply color order
                if r_order == 0:
                    first = r
                elif r_order == 1:
                    first = g
                else:
                    first = b
                    
                if g_order == 0:
                    second = r
                elif g_order == 1:
                    second = g
                else:
                    second = b
                    
                if b_order == 0:
                    third = r
                elif b_order == 1:
                    third = g
                else:
                    third = b
                
                buffer.extend([first, second, third])
            
            # Add padding bytes to reach stride
            buffer.extend([0x00] * PADDING_BYTES_PER_LINE)
        
        return bytes(buffer)
    except Exception as e:
        print(f"Error creating RGB buffer: {e}")
        return None

def write_to_file(data, filename="/tmp/gm12u320_image.rgb"):
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

def test_color_combination(test_number, r_order, g_order, b_order, duration=5):
    """Test a specific color combination"""
    print(f"\n--- Test {test_number:02d}: RGB Order {r_order}{g_order}{b_order} ---")
    
    # Create test pattern
    image = create_color_test_pattern(test_number, r_order, g_order, b_order)
    if image is None:
        print("Failed to create test pattern")
        return False
    
    # Convert to buffer with custom color order
    data = create_rgb_buffer_with_stride(image, r_order, g_order, b_order)
    if data is None:
        print("Failed to create RGB buffer")
        return False
    
    # Write to file
    if not write_to_file(data):
        print("Failed to write to file")
        return False
    
    print(f"Test {test_number:02d} displayed for {duration} seconds")
    print("Check the projector and note the colors")
    print("Press Enter to continue to next test, or 'q' to quit")
    
    # Wait for user input or timeout
    try:
        import select
        
        start_time = time.time()
        while time.time() - start_time < duration:
            if os.name == 'nt':  # Windows
                try:
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        if key == 'q':
                            return 'quit'
                        elif key == '\r':
                            break
                except:
                    pass
            else:  # Unix/Linux/Mac
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.readline().strip().lower()
                    if key == 'q':
                        return 'quit'
                    elif key == '':
                        break
            time.sleep(0.1)
    except:
        time.sleep(duration)
    
    return True

def main():
    print("GM12U320 Color Calibration")
    print("==========================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("Projector device /dev/dri/card2 not found")
        print("Please make sure the GM12U320 driver is loaded")
        return 1
    
    print("Projector device found: /dev/dri/card2")
    print("\nThis script will test different RGB color orders")
    print("Each test will show for 5 seconds")
    print("Look for the test number and color bars")
    print("Note which test shows correct colors")
    
    # Color order combinations to test
    # 0=R, 1=G, 2=B
    color_combinations = [
        (0, 1, 2),  # RGB (standard)
        (2, 1, 0),  # BGR (common swap)
        (1, 0, 2),  # GRB
        (0, 2, 1),  # RBG
        (2, 0, 1),  # BRG
        (1, 2, 0),  # GBR
    ]
    
    print(f"\nWill test {len(color_combinations)} color combinations")
    print("Press Enter to start, or 'q' to quit")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled")
        return 0
    
    # Run tests
    for i, (r_order, g_order, b_order) in enumerate(color_combinations):
        test_number = i + 1
        result = test_color_combination(test_number, r_order, g_order, b_order)
        
        if result == 'quit':
            print("\nCalibration stopped by user")
            break
        elif not result:
            print(f"Test {test_number} failed, continuing...")
    
    # Cleanup
    try:
        os.remove("/tmp/gm12u320_image.rgb")
        print("Test file removed")
    except:
        pass
    
    print("\nCalibration complete!")
    print("Note which test number showed correct colors")
    print("You can then modify show_image.py to use that color order")

if __name__ == "__main__":
    sys.exit(main())