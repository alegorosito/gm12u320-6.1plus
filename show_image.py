#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
Simplified version with 3 main options:
1. Test pattern (default, no arguments)
2. Image/Video file
3. Screen capture

Requirements:
- PIL (Pillow) with ImageGrab support
- OpenCV (cv2) for video support
- On Linux: may need additional packages for screen capture
- On macOS: requires screen recording permissions
- On Windows: should work out of the box
"""

import numpy as np
import os
import sys
import time
from PIL import Image, ImageGrab

# Try to import OpenCV for video support
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("⚠️  OpenCV no está instalado. El soporte de video estará deshabilitado.")
    print("   Instala con: pip install opencv-python")

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
        print(f"📷 Cargando imagen: {image_path}")
        image = Image.open(image_path)
        print(f"   Imagen cargada: {image.size[0]}x{image.size[1]} píxeles")
        return image
    except Exception as e:
        print(f"❌ Error cargando imagen: {e}")
        return None

def is_video_file(filename):
    """Check if file is a video based on extension"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def load_video_frame(video_path, frame_number=0):
    """Load a frame from video file"""
    if not HAS_OPENCV:
        print("❌ OpenCV no está disponible para reproducir video")
        return None
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ No se pudo abrir el video: {video_path}")
            return None
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"🎬 Video cargado: {video_path}")
        print(f"   FPS: {fps:.2f}, Frames: {total_frames}, Duración: {duration:.1f}s")
        
        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            # Convert BGR to RGB for PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            cap.release()
            return image, fps, total_frames
        else:
            cap.release()
            return None, fps, total_frames
    except Exception as e:
        print(f"❌ Error cargando video: {e}")
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
    """Capture screen using PIL ImageGrab (cross-platform)"""
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
                if attempt < max_retries - 1:
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

def main():
    print("GM12U320 Projector Image Display")
    print("=================================")
    
    # Check if projector device exists
    if not os.path.exists('/dev/dri/card2'):
        print("❌ Dispositivo /dev/dri/card2 no encontrado")
        print("   Asegúrate de que el driver GM12U320 esté cargado")
        return 1
    
    print("✅ Dispositivo encontrado: /dev/dri/card2")
    
    # Parse arguments - SIMPLIFIED
    fps = 10  # Default FPS
    mode = "test"  # test, image, video, screen
    source_file = None
    video_info = None  # (fps, total_frames) for video
    
    if len(sys.argv) == 1:
        # No arguments: test pattern at default FPS
        mode = "test"
        print("\n🎨 Modo: Patrón de prueba (por defecto)")
        print(f"   FPS: {fps}")
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        # Check if it's a number (FPS for test pattern)
        try:
            fps = float(arg)
            if fps <= 0 or fps > 60:
                print("❌ FPS debe estar entre 0.1 y 60")
                return 1
            mode = "test"
            print(f"\n🎨 Modo: Patrón de prueba")
            print(f"   FPS: {fps}")
        except ValueError:
            # Not a number, check if it's a file or "screen"
            if arg.lower() == "screen":
                mode = "screen"
                print("\n📸 Modo: Captura de pantalla principal")
            elif os.path.exists(arg):
                if is_video_file(arg):
                    mode = "video"
                    source_file = arg
                    print(f"\n🎬 Modo: Reproducción de video")
                    print(f"   Archivo: {arg}")
                else:
                    mode = "image"
                    source_file = arg
                    print(f"\n📷 Modo: Imagen estática")
                    print(f"   Archivo: {arg}")
            else:
                print(f"❌ Archivo no encontrado: {arg}")
                print("\nUso:")
                print("  python3 show_image.py              # Patrón de prueba (10 FPS)")
                print("  python3 show_image.py 24           # Patrón de prueba a 24 FPS")
                print("  python3 show_image.py 24 screen    # Captura de pantalla a 24 FPS")
                print("  python3 show_image.py imagen.jpg   # Mostrar imagen")
                print("  python3 show_image.py video.mp4     # Reproducir video")
                print("  python3 show_image.py screen       # Capturar pantalla principal (10 FPS)")
                return 1
    elif len(sys.argv) == 3:
        # Two arguments: FPS and mode/file
        arg1 = sys.argv[1]
        arg2 = sys.argv[2]
        
        # First argument should be FPS
        try:
            fps = float(arg1)
            if fps <= 0 or fps > 60:
                print("❌ FPS debe estar entre 0.1 y 60")
                return 1
        except ValueError:
            print("❌ El primer argumento debe ser un número (FPS)")
            print("\nUso:")
            print("  python3 show_image.py 24 screen    # Captura de pantalla a 24 FPS")
            print("  python3 show_image.py 30 screen     # Captura de pantalla a 30 FPS")
            return 1
        
        # Second argument: mode or file
        if arg2.lower() == "screen":
            mode = "screen"
            print(f"\n📸 Modo: Captura de pantalla principal")
            print(f"   FPS: {fps}")
        elif os.path.exists(arg2):
            if is_video_file(arg2):
                mode = "video"
                source_file = arg2
                print(f"\n🎬 Modo: Reproducción de video")
                print(f"   Archivo: {arg2}")
                print(f"   FPS solicitado: {fps} (se usará FPS del video si está disponible)")
            else:
                mode = "image"
                source_file = arg2
                print(f"\n📷 Modo: Imagen estática")
                print(f"   Archivo: {arg2}")
                print(f"   FPS: {fps}")
        else:
            print(f"❌ Segundo argumento inválido: {arg2}")
            print("\nUso:")
            print("  python3 show_image.py 24 screen    # Captura de pantalla a 24 FPS")
            print("  python3 show_image.py 30 screen     # Captura de pantalla a 30 FPS")
            print("  python3 show_image.py 10 imagen.jpg # Imagen a 10 FPS")
            return 1
    else:
        print("❌ Demasiados argumentos")
        print("\nUso:")
        print("  python3 show_image.py              # Patrón de prueba (10 FPS)")
        print("  python3 show_image.py 24           # Patrón de prueba a 24 FPS")
        print("  python3 show_image.py 24 screen    # Captura de pantalla a 24 FPS")
        print("  python3 show_image.py imagen.jpg   # Mostrar imagen")
        print("  python3 show_image.py video.mp4     # Reproducir video")
        print("  python3 show_image.py screen       # Capturar pantalla principal (10 FPS)")
        return 1
    
    # Set default resolution
    if not set_resolution(DEFAULT_RESOLUTION):
        return 1
    
    # Calculate frame interval
    frame_interval = 1.0 / fps
    print(f"   Intervalo: {frame_interval:.3f} segundos")
    print("   Presiona Ctrl+C para detener\n")
    
    # Load content based on mode
    use_static_image = False
    static_data = None
    video_cap = None
    video_fps = None
    video_total_frames = 0
    video_frame_number = 0
    
    if mode == "image":
        image = load_image_from_path(source_file)
        if image:
            resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
            if resized_image:
                static_data = create_rgb_buffer_with_stride(resized_image, verbose=False)
                if static_data:
                    use_static_image = True
        if not use_static_image:
            print("⚠️  No se pudo cargar la imagen, usando patrón de prueba")
            mode = "test"
    elif mode == "video":
        if not HAS_OPENCV:
            print("⚠️  OpenCV no disponible, usando patrón de prueba")
            mode = "test"
        else:
            video_cap = cv2.VideoCapture(source_file)
            if not video_cap.isOpened():
                print("⚠️  No se pudo abrir el video, usando patrón de prueba")
                mode = "test"
            else:
                video_fps = video_cap.get(cv2.CAP_PROP_FPS)
                video_total_frames = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                print(f"   FPS del video: {video_fps:.2f}, Frames totales: {video_total_frames}")
                # Use video FPS if available, otherwise use specified FPS
                if video_fps > 0:
                    fps = video_fps
                    frame_interval = 1.0 / fps
                    print(f"   Usando FPS del video: {fps:.2f}")
    elif mode == "screen":
        print("📸 Capturando pantalla principal...")
        # Will capture continuously in the loop
    
    # Main refresh loop
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            frame_start = time.time()
            data = None
            
            if mode == "screen":
                # Capture screen continuously
                image = capture_screen_with_retry(max_retries=2)
                if image is not None:
                    resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
                    if resized_image is not None:
                        data = create_rgb_buffer_with_stride(resized_image, verbose=False)
                        if data and write_to_file(data, verbose=False):
                            frame_count += 1
                            if frame_count % 10 == 0:
                                monitor_performance(frame_count, start_time, image.size)
                else:
                    print("⚠️  Captura fallida, reintentando...")
                    
            elif mode == "video":
                # Read next frame from video
                if video_cap and video_cap.isOpened():
                    ret, frame = video_cap.read()
                    if ret:
                        # Convert BGR to RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        image = Image.fromarray(frame_rgb)
                        resized_image = resize_image(image, PROJECTOR_WIDTH, PROJECTOR_HEIGHT)
                        if resized_image:
                            data = create_rgb_buffer_with_stride(resized_image, verbose=False)
                            if data and write_to_file(data, verbose=False):
                                frame_count += 1
                                video_frame_number += 1
                                if frame_count % 30 == 0:
                                    progress = (video_frame_number / video_total_frames * 100) if video_total_frames > 0 else 0
                                    print(f"Frame {frame_count} | Video: {video_frame_number}/{video_total_frames} ({progress:.1f}%)")
                    else:
                        # End of video, restart
                        video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        video_frame_number = 0
                        print("🔄 Video reiniciado")
                        
            elif mode == "image":
                # Static image
                if static_data:
                    data = static_data
                    if write_to_file(data, verbose=False):
                        frame_count += 1
                        if frame_count % 10 == 0:
                            monitor_performance(frame_count, start_time)
                            
            else:  # mode == "test"
                # Test pattern
                data = create_test_pattern(frame_count)
                if data and write_to_file(data, verbose=False):
                    frame_count += 1
                    if frame_count % 10 == 0:
                        monitor_performance(frame_count, start_time)
            
            # Calculate sleep time to maintain FPS
            frame_time = time.time() - frame_start
            sleep_time = max(0, frame_interval - frame_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo...")
        
        # Cleanup
        if video_cap:
            video_cap.release()
        
        try:
            os.remove("/tmp/gm12u320_image.rgb")
        except:
            pass
        
        # Final stats
        total_time = time.time() - start_time
        final_fps = frame_count / total_time if total_time > 0 else 0
        print(f"📊 Estadísticas finales:")
        print(f"   Frames: {frame_count}")
        print(f"   Tiempo: {total_time:.1f}s")
        print(f"   FPS promedio: {final_fps:.1f}")
        
        if mode == "video":
            print(f"   Video reproducido: {video_frame_number} frames")
        
        print("\n✅ Proyección detenida")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 