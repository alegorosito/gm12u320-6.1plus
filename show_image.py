#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Supports 800x600 and 1024x768 resolutions with proper stride handling
Can display images from file, URL, or capture screen continuously

Requirements:
- PIL (Pillow) with ImageGrab support
- On Linux: may need additional packages for screen capture
- On macOS: requires screen recording permissions
- On Windows: should work out of the box
"""

import numpy as np
import os
import sys
import time
import subprocess
from PIL import Image, ImageGrab
import requests
import io

# Resolution configurations
RESOLUTIONS = {
    '800x600': {
        'width': 800,
        'height': 600,
        'stride': 2562,  # 2400 data + 162 padding
        'data_bytes_per_line': 2400,
        'padding_bytes_per_line': 162,
        'total_size': 1537200
    },
    '1024x768': {
        'width': 1024,
        'height': 768,
        'stride': 3072,  # 3072 data + 0 padding (aligned)
        'data_bytes_per_line': 3072,
        'padding_bytes_per_line': 0,
        'total_size': 2359296
    }
}

# Default resolution
DEFAULT_RESOLUTION = '800x600'
BYTES_PER_PIXEL = 3

# Global resolution settings (will be set by command line)
PROJECTOR_WIDTH = RESOLUTIONS[DEFAULT_RESOLUTION]['width']
PROJECTOR_HEIGHT = RESOLUTIONS[DEFAULT_RESOLUTION]['height']
STRIDE_BYTES_PER_LINE = RESOLUTIONS[DEFAULT_RESOLUTION]['stride']
DATA_BYTES_PER_LINE = RESOLUTIONS[DEFAULT_RESOLUTION]['data_bytes_per_line']
PADDING_BYTES_PER_LINE = RESOLUTIONS[DEFAULT_RESOLUTION]['padding_bytes_per_line']
TOTAL_FILE_SIZE = RESOLUTIONS[DEFAULT_RESOLUTION]['total_size']

# Global device path (will be set by driver detection)
PROJECTOR_DEVICE = None

def set_resolution(resolution_name):
    """Set the global resolution settings"""
    global PROJECTOR_WIDTH, PROJECTOR_HEIGHT, STRIDE_BYTES_PER_LINE
    global DATA_BYTES_PER_LINE, PADDING_BYTES_PER_LINE, TOTAL_FILE_SIZE
    
    if resolution_name not in RESOLUTIONS:
        print(f"Invalid resolution: {resolution_name}")
        print(f"Available resolutions: {', '.join(RESOLUTIONS.keys())}")
        return False
    
    config = RESOLUTIONS[resolution_name]
    PROJECTOR_WIDTH = config['width']
    PROJECTOR_HEIGHT = config['height']
    STRIDE_BYTES_PER_LINE = config['stride']
    DATA_BYTES_PER_LINE = config['data_bytes_per_line']
    PADDING_BYTES_PER_LINE = config['padding_bytes_per_line']
    TOTAL_FILE_SIZE = config['total_size']
    
    print(f"Resolution set to: {resolution_name}")
    print(f"Dimensions: {PROJECTOR_WIDTH}x{PROJECTOR_HEIGHT}")
    print(f"Stride: {STRIDE_BYTES_PER_LINE} bytes per line")
    print(f"Total file size: {TOTAL_FILE_SIZE} bytes")
    return True

def load_image_from_path(image_path):
    """Load image from local file path"""
    try:
        print(f"Loading image from: {image_path}")
        image = Image.open(image_path)
        print(f"Image loaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

def download_image(url):
    """Download image from URL"""
    try:
        print(f"Downloading image from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        print(f"Image downloaded: {image.size[0]}x{image.size[1]} pixels")
        return image
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def resize_image(image, target_width, target_height):
    """Resize image to exact projector resolution - OPTIMIZED"""
    try:
        # Use faster resampling for better performance
        resized_image = image.resize((target_width, target_height), Image.Resampling.NEAREST)
        return resized_image
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None

def create_rgb_buffer_with_stride(image, verbose=True):
    """Convert PIL image to RGB buffer with proper stride and padding - OPTIMIZED"""
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        array = np.array(image, dtype=np.uint8)
        
        # Create output buffer with proper stride - OPTIMIZED
        output_buffer = np.zeros((PROJECTOR_HEIGHT, STRIDE_BYTES_PER_LINE), dtype=np.uint8)
        
        # Copy RGB data and convert to BGR in one operation
        # array shape is (height, width, 3) - RGB
        # We need BGR order and proper stride
        for y in range(PROJECTOR_HEIGHT):
            # Copy RGB data and convert to BGR in one slice operation
            output_buffer[y, 0:DATA_BYTES_PER_LINE:3] = array[y, :, 2]  # B (was R)
            output_buffer[y, 1:DATA_BYTES_PER_LINE:3] = array[y, :, 1]  # G
            output_buffer[y, 2:DATA_BYTES_PER_LINE:3] = array[y, :, 0]  # R (was B)
        
        # Padding is already zeros from np.zeros()
        
        if verbose:
            print(f"Buffer created: {output_buffer.nbytes} bytes")
            print(f"Expected size: {TOTAL_FILE_SIZE} bytes")
            print(f"Data bytes per line: {DATA_BYTES_PER_LINE}")
            print(f"Padding bytes per line: {PADDING_BYTES_PER_LINE}")
            print(f"Total stride per line: {STRIDE_BYTES_PER_LINE}")
            print(f"Color order: BGR (optimized)")
        
        return output_buffer.tobytes()
    except Exception as e:
        print(f"Error creating RGB buffer: {e}")
        return None

def capture_screen():
    """Capture screen using PIL ImageGrab (cross-platform) - IMPROVED"""
    try:
        # Capture the entire screen
        image = ImageGrab.grab()
        
        # Validate the captured image
        if image is None or image.size[0] == 0 or image.size[1] == 0:
            print("⚠️  Screen capture returned invalid image")
            return None
            
        # Check if image has valid dimensions
        if image.size[0] < 100 or image.size[1] < 100:
            print(f"⚠️  Screen capture returned suspicious size: {image.size}")
            return None
            
        return image
        
    except Exception as e:
        print(f"❌ Screen capture error: {e}")
        return None

def capture_screen_with_retry(max_retries=3):
    """Capture screen with retry logic for better reliability"""
    for attempt in range(max_retries):
        try:
            image = capture_screen()
            if image is not None:
                return image
            else:
                print(f"⚠️  Capture attempt {attempt + 1} failed, retrying...")
                time.sleep(0.1)  # Short delay before retry
        except Exception as e:
            print(f"⚠️  Capture attempt {attempt + 1} error: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)
    
    print("❌ All screen capture attempts failed")
    return None

def monitor_performance(frame_count, start_time, image_size=None):
    """Monitor and display performance statistics"""
    elapsed = time.time() - start_time
    actual_fps = frame_count / elapsed if elapsed > 0 else 0
    
    if image_size:
        print(f"Frame {frame_count} | FPS: {actual_fps:.1f} | Time: {elapsed:.1f}s | Screen: {image_size[0]}x{image_size[1]}")
    else:
        print(f"Frame {frame_count} | FPS: {actual_fps:.1f} | Time: {elapsed:.1f}s")

def create_test_pattern(frame_number=0):
    """Create animated test pattern with proper stride - OPTIMIZED"""
    try:
        # Create output buffer with proper stride
        output_buffer = np.zeros((PROJECTOR_HEIGHT, STRIDE_BYTES_PER_LINE), dtype=np.uint8)
        
        # Create coordinate arrays for vectorized operations
        x_coords = np.arange(PROJECTOR_WIDTH)
        y_coords = np.arange(PROJECTOR_HEIGHT)
        
        # Create RGB values using vectorized operations
        r_values = (x_coords * 255 + frame_number * 10) % 256
        g_values = (y_coords * 255 + frame_number * 15) % 256
        b_values = (128 + frame_number * 20) % 256
        
        # Fill the buffer with BGR data
        for y in range(PROJECTOR_HEIGHT):
            # Copy BGR data in one operation
            output_buffer[y, 0:DATA_BYTES_PER_LINE:3] = b_values  # B
            output_buffer[y, 1:DATA_BYTES_PER_LINE:3] = g_values[y]  # G
            output_buffer[y, 2:DATA_BYTES_PER_LINE:3] = r_values  # R
        
        # Padding is already zeros from np.zeros()
        
        return output_buffer.tobytes()
    except Exception as e:
        print(f"Error creating test pattern: {e}")
        return None

def create_error_pattern(frame_number=0):
    """Create a simple error pattern for when screen capture fails."""
    try:
        output_buffer = np.zeros((PROJECTOR_HEIGHT, STRIDE_BYTES_PER_LINE), dtype=np.uint8)
        
        # Create a simple red pattern
        for y in range(PROJECTOR_HEIGHT):
            output_buffer[y, 0:DATA_BYTES_PER_LINE:3] = 255 # Red
            output_buffer[y, 1:DATA_BYTES_PER_LINE:3] = 0   # Green
            output_buffer[y, 2:DATA_BYTES_PER_LINE:3] = 0   # Blue
        
        return output_buffer.tobytes()
    except Exception as e:
        print(f"Error creating error pattern: {e}")
        return None

def write_to_file(data, filename="/tmp/gm12u320_image.rgb", verbose=True):
    """Write data to file with validation - OPTIMIZED"""
    try:
        # Use direct write without flush/fsync for better performance
        with open(filename, 'wb') as f:
            f.write(data)
            # Only flush if verbose (for debugging)
            if verbose:
                f.flush()
                os.fsync(f.fileno())
        
        # Only validate file size if verbose
        if verbose:
            file_size = os.path.getsize(filename)
            print(f"File written: {filename}")
            print(f"File size: {file_size} bytes")
            
            if file_size == TOTAL_FILE_SIZE:
                print("File size validation: PASSED")
            else:
                print(f"File size validation: FAILED (expected {TOTAL_FILE_SIZE}, got {file_size})")
                return False
        
        return True
            
    except Exception as e:
        print(f"Error writing to file: {e}")
        return False

def is_module_loaded(module_name="gm12u320"):
    """Check if a kernel module is loaded"""
    try:
        # Check /proc/modules for the module
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            return module_name in modules
    except FileNotFoundError:
        # Fallback to lsmod command
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=2)
            return module_name in result.stdout
        except:
            return False
    except Exception as e:
        print(f"Error checking module: {e}")
        return False

def find_dri_device():
    """Find the DRI device for the projector (card0, card1, card2, etc.)"""
    # Common DRI device paths
    possible_devices = ['/dev/dri/card0', '/dev/dri/card1', '/dev/dri/card2', '/dev/dri/card3']
    
    for device in possible_devices:
        if os.path.exists(device):
            # Check if it's the gm12u320 device by checking sysfs
            try:
                # Check if the device is associated with gm12u320
                device_num = device.split('card')[-1]
                sysfs_path = f'/sys/class/drm/card{device_num}/device/uevent'
                if os.path.exists(sysfs_path):
                    with open(sysfs_path, 'r') as f:
                        uevent = f.read()
                        if 'gm12u320' in uevent.lower():
                            return device
            except:
                pass
    
    # If no specific device found, return the first available card
    for device in possible_devices:
        if os.path.exists(device):
            return device
    
    return None

def load_driver_module(module_name="gm12u320", auto_load=True):
    """Load the driver module if not already loaded"""
    # Check if module is already loaded
    if is_module_loaded(module_name):
        print(f"✅ Driver module '{module_name}' is already loaded")
        return True
    
    if not auto_load:
        print(f"⚠️  Driver module '{module_name}' is not loaded")
        print(f"   Please load it manually with: sudo modprobe {module_name}")
        return False
    
    print(f"📦 Driver module '{module_name}' not found, attempting to load...")
    
    # Try to load the module
    try:
        # First try modprobe (recommended method)
        result = subprocess.run(
            ['sudo', 'modprobe', module_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ Successfully loaded driver module '{module_name}'")
            # Wait a moment for the device to appear
            time.sleep(1)
            return True
        else:
            print(f"❌ Failed to load module with modprobe: {result.stderr}")
            
            # Try insmod as fallback (requires full path)
            print("   Trying alternative method...")
            module_paths = [
                f'/lib/modules/{os.uname().release}/updates/dkms/{module_name}.ko',
                f'/lib/modules/{os.uname().release}/extra/{module_name}.ko',
                f'/lib/modules/{os.uname().release}/kernel/drivers/gpu/drm/{module_name}/{module_name}.ko',
            ]
            
            for path in module_paths:
                if os.path.exists(path):
                    result = subprocess.run(
                        ['sudo', 'insmod', path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        print(f"✅ Successfully loaded driver module from {path}")
                        time.sleep(1)
                        return True
            
            print(f"❌ Could not load module '{module_name}'")
            print(f"   Please install the driver first:")
            print(f"   1. Build: make")
            print(f"   2. Install: sudo make modules_install")
            print(f"   3. Load: sudo modprobe {module_name}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout while loading module '{module_name}'")
        return False
    except FileNotFoundError:
        print(f"❌ 'modprobe' command not found. Please load the module manually:")
        print(f"   sudo modprobe {module_name}")
        return False
    except Exception as e:
        print(f"❌ Error loading module: {e}")
        return False

def check_and_setup_driver(auto_load=True):
    """Check if driver is loaded and device exists, load if needed"""
    module_name = "gm12u320"
    
    # Step 1: Check if module is loaded
    if not is_module_loaded(module_name):
        if not auto_load:
            print(f"❌ Driver module '{module_name}' is not loaded")
            print(f"   Please load it with: sudo modprobe {module_name}")
            return None, False
        
        # Try to load the module
        if not load_driver_module(module_name, auto_load=True):
            return None, False
    
    # Step 2: Find the DRI device
    device_path = find_dri_device()
    
    if device_path is None:
        print("⚠️  No DRI device found")
        print("   The driver may be loaded but the device is not connected")
        print("   Please check:")
        print("   1. Is the projector connected via USB?")
        print("   2. Is the USB device recognized? (lsusb)")
        return None, False
    
    print(f"✅ Found projector device: {device_path}")
    return device_path, True

def main():
    print("GM12U320 Projector Image Display")
    print("=================================")
    
    # Parse command line arguments first to check for auto-load flag
    auto_load_driver = True
    
    if len(sys.argv) > 1:
        # Check for special flags first
        if '--no-auto-load' in sys.argv or '--manual' in sys.argv:
            auto_load_driver = False
            sys.argv.remove('--no-auto-load' if '--no-auto-load' in sys.argv else '--manual')
    
    # Check and setup driver (auto-load if needed)
    device_path, driver_ok = check_and_setup_driver(auto_load=auto_load_driver)
    
    if not driver_ok or device_path is None:
        print("\n❌ Driver setup failed")
        print("Please ensure:")
        print("  1. The driver is installed (make && sudo make modules_install)")
        print("  2. The projector is connected via USB")
        print("  3. You have sudo permissions to load modules")
        return 1
    
    # Store device path for later use (if needed)
    global PROJECTOR_DEVICE
    PROJECTOR_DEVICE = device_path
    
    # Show usage if no arguments provided
    if len(sys.argv) == 1:
        print("\nUsage:")
        print("  python3 show_image.py [FPS] [source] [resolution] [--no-auto-load]")
        print("\nExamples:")
        print("  python3 show_image.py 24 live 800x600     # Live capture at 24 FPS, 800x600")
        print("  python3 show_image.py 30 live 1024x768    # Live capture at 30 FPS, 1024x768")
        print("  python3 show_image.py 24 fast             # Performance mode at 24 FPS")
        print("  python3 show_image.py 10 screen           # Single screen capture")
        print("  python3 show_image.py 10 image.jpg        # Static image")
        print("  python3 show_image.py                     # Test pattern")
        print("\nOptions:")
        print("  --no-auto-load    Don't automatically load the driver module")
        print("\nAvailable resolutions: 800x600, 1024x768")
        print("Note: 1024x768 requires more processing power but provides higher resolution")
        print("Press Ctrl+C to stop")
        print()
    
    # Parse command line arguments
    fps = 10  # Default FPS
    image_source = None
    resolution = DEFAULT_RESOLUTION
    continuous_capture = False
    performance_mode = False
    
    if len(sys.argv) > 1:
        
        # Check if first argument is FPS
        try:
            fps = float(sys.argv[1])
            if fps <= 0 or fps > 60:
                print("FPS must be between 0.1 and 60")
                return 1
            print(f"Using FPS: {fps}")
            
            # Check for additional arguments
            if len(sys.argv) > 2:
                image_source = sys.argv[2]
            if len(sys.argv) > 3:
                resolution = sys.argv[3]
        except ValueError:
            # First argument is not FPS, treat as image source
            image_source = sys.argv[1]
            if len(sys.argv) > 2:
                resolution = sys.argv[2]
    
    # Set resolution
    if not set_resolution(resolution):
        return 1
    
    # Calculate frame interval
    frame_interval = 1.0 / fps
    print(f"Frame interval: {frame_interval:.3f} seconds")
    
    # Check for continuous capture mode
    if image_source == "live" or image_source == "continuous":
        continuous_capture = True
        performance_mode = True  # Enable performance mode for live capture
        print("🎥 Continuous screen capture mode enabled")
        print(f"📸 Capturing screen at {fps} FPS")
        print("⚡ Performance mode enabled for optimal FPS")
    elif image_source == "fast" or image_source == "performance":
        performance_mode = True
        print("⚡ Performance mode enabled")
        print("Use 'live' or 'continuous' for real-time capture")
    elif image_source:
        if image_source == "screen" or image_source == "capture":
            print("Capturing single screen for projector")
            image = capture_screen()
        elif os.path.exists(image_source):
            print(f"Using local image file: {image_source}")
            image = load_image_from_path(image_source)
        elif image_source.startswith(('http://', 'https://')):
            print(f"Using custom image URL: {image_source}")
            image = download_image(image_source)
        else:
            print(f"Invalid image source: {image_source}")
            print("Usage examples:")
            print("  python3 show_image.py 24 live 800x600     # Live capture at 24 FPS, 800x600")
            print("  python3 show_image.py 30 live 1024x768    # Live capture at 30 FPS, 1024x768")
            print("  python3 show_image.py 24 fast             # Performance mode at 24 FPS")
            print("  python3 show_image.py 10 screen           # Single screen capture")
            print("  python3 show_image.py 10 image.jpg        # Static image")
            print("  python3 show_image.py                     # Test pattern")
            image = None
            
        if image is None:
            print("Using animated test pattern instead")
            use_static_image = False
        else:
            # Resize image
            resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized_image is None:
                print("Using animated test pattern instead")
                use_static_image = False
            else:
                # Convert to RGB buffer with stride
                static_data = create_rgb_buffer_with_stride(resized_image)
                if static_data is None:
                    print("Using animated test pattern instead")
                    use_static_image = False
                else:
                    use_static_image = True
    else:
        print("Using animated test pattern")
        use_static_image = False
    
    print(f"Refresh rate: {fps} FPS")
    print("Press Ctrl+C to stop")
    
    # Main refresh loop
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            frame_start = time.time()
            
            if continuous_capture:
                # Capture screen continuously - IMPROVED with retry logic
                image = capture_screen_with_retry(max_retries=2)
                if image is not None:
                    # Resize to projector resolution
                    resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
                    if resized_image is not None:
                        # Convert to RGB buffer with stride (quiet mode for continuous capture)
                        data = create_rgb_buffer_with_stride(resized_image, verbose=False)
                        if data:
                            # Write to file (quiet mode for continuous capture)
                            if write_to_file(data, verbose=False):
                                frame_count += 1
                                
                                # Calculate and display stats every 10 frames
                                if frame_count % 10 == 0:
                                    monitor_performance(frame_count, start_time, image.size)
                            else:
                                print("⚠️  File write failed, retrying next frame")
                        else:
                            print("⚠️  Buffer creation failed, retrying next frame")
                    else:
                        print("⚠️  Image resize failed, retrying next frame")
                else:
                    # If all capture attempts fail, show a brief error pattern instead of test pattern
                    print("⚠️  Screen capture failed, showing error pattern")
                    error_data = create_error_pattern(frame_count)
                    if error_data and write_to_file(error_data, verbose=False):
                        frame_count += 1
                        
                        # Calculate and display stats every 10 frames
                        if frame_count % 10 == 0:
                            monitor_performance(frame_count, start_time)
            elif use_static_image:
                # Use static image - OPTIMIZED
                data = static_data
                if data and write_to_file(data, verbose=False):
                    frame_count += 1
                    
                    # Calculate and display stats every 10 frames
                    if frame_count % 10 == 0:
                        monitor_performance(frame_count, start_time)
            else:
                # Create animated test pattern - OPTIMIZED
                data = create_test_pattern(frame_count)
                if data and write_to_file(data, verbose=False):
                    frame_count += 1
                    
                    # Calculate and display stats every 10 frames
                    if frame_count % 10 == 0:
                        monitor_performance(frame_count, start_time)
            
            # Calculate sleep time to maintain FPS
            frame_time = time.time() - frame_start
            sleep_time = max(0, frame_interval - frame_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nStopping image display")
        try:
            os.remove("/tmp/temp_screen.jpg")
            os.remove("/tmp/gm12u320_image.rgb")
            if continuous_capture:
                print("Live capture stopped, projector will show test pattern")
            else:
                print("Image files removed, projector will show test pattern")
        except:
            pass
        
        # Final stats
        total_time = time.time() - start_time
        final_fps = frame_count / total_time if total_time > 0 else 0
        print(f"Final stats: {frame_count} frames in {total_time:.1f}s = {final_fps:.1f} FPS")
        if continuous_capture:
            print("Live screen capture completed")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 