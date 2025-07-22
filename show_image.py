#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
=======================================
✅ Modo normal: muestra una imagen llenando toda la pantalla del proyector.
✅ Modo test: recorre automáticamente combinaciones de stride / bgr / escalado para diagnóstico.

Uso:
----
Normal:
    python3 show_image.py <imagen_local|url>

Test automático:
    python3 show_image.py --test <imagen_local|url>

Logs:
-----
Guarda los resultados en: gm12u320_test.log
"""

import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io, time, sys, os, datetime

# 📐 Configuración hardware
PROJECTOR_WIDTH = 800
PROJECTOR_HEIGHT = 600
PROJECTOR_BYTES_PER_PIXEL = 3  # RGB
DEFAULT_STRIDE = 2560
LOG_FILE = "gm12u320_test.log"

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()}: {msg}\n")

def load_image(image_source):
    """Carga imagen local o descarga de URL"""
    try:
        if os.path.exists(image_source):
            log(f"📂 Loading local image: {image_source}")
            image = Image.open(image_source)
        elif image_source.startswith(('http://', 'https://')):
            log(f"📥 Downloading image from: {image_source}")
            r = requests.get(image_source, timeout=10)
            r.raise_for_status()
            image = Image.open(io.BytesIO(r.content))
        else:
            log("❌ Invalid image source.")
            return None
        log(f"✅ Image loaded: {image.size[0]}x{image.size[1]}")
        return image
    except Exception as e:
        log(f"❌ Error loading image: {e}")
        return None

def resize_image(image, mode="Exact-fit"):
    if mode == "Exact-fit":
        resized = image.resize((PROJECTOR_WIDTH, PROJECTOR_HEIGHT), Image.Resampling.LANCZOS)
        log(f"✅ Image resized to exact {PROJECTOR_WIDTH}x{PROJECTOR_HEIGHT}")
    else:
        img_w, img_h = image.size
        target_ratio = PROJECTOR_WIDTH / PROJECTOR_HEIGHT
        img_ratio = img_w / img_h
        if img_ratio > target_ratio:
            new_w = PROJECTOR_WIDTH
            new_h = int(PROJECTOR_WIDTH / img_ratio)
        else:
            new_h = PROJECTOR_HEIGHT
            new_w = int(PROJECTOR_HEIGHT * img_ratio)
        resized = Image.new("RGB", (PROJECTOR_WIDTH, PROJECTOR_HEIGHT), (0,0,0))
        tmp = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        x = (PROJECTOR_WIDTH - new_w) // 2
        y = (PROJECTOR_HEIGHT - new_h) // 2
        resized.paste(tmp, (x,y))
        log(f"✅ Image resized aspect-fit to {new_w}x{new_h} centered")
    return resized

def image_to_rgb_array_with_stride(image, expected_stride=DEFAULT_STRIDE, swap_bgr=False):
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        array = np.array(image, dtype=np.uint8)
        if swap_bgr:
            array = array[:, :, ::-1]
        h, w, _ = array.shape
        line_bytes = w * 3
        if expected_stride <= line_bytes:
            log(f"✅ No stride adjustment needed ({line_bytes} bytes/line)")
            return array.tobytes()
        padding = expected_stride - line_bytes
        log(f"ℹ️ Adding {padding} padding bytes per line (expected stride: {expected_stride})")
        buffer = bytearray()
        for y in range(h):
            buffer += array[y,:,:].tobytes()
            buffer += b'\x00' * padding
        log(f"✅ Image converted: stride={expected_stride}, swap_bgr={swap_bgr}")
        return bytes(buffer)
    except Exception as e:
        log(f"❌ Error preparing RGB data: {e}")
        return None

def write_image_to_file(rgb_bytes, filename="/tmp/gm12u320_image.rgb"):
    try:
        with open(filename, 'wb') as f:
            f.write(rgb_bytes)
            f.flush()
            os.fsync(f.fileno())
        log(f"✅ Image written to {filename}")
        return True
    except Exception as e:
        log(f"❌ Error writing image: {e}")
        return False

def check_projector_status():
    log("🎥 Checking projector device /dev/dri/card2 …")
    if not os.path.exists('/dev/dri/card2'):
        log("❌ Projector device /dev/dri/card2 not found.")
        return False
    log("✅ Projector detected.")
    return True

def cleanup():
    try:
        os.remove("/tmp/gm12u320_image.rgb")
        log("🧹 Removed temporary image file.")
    except:
        pass

def run_normal(image_source):
    log("🎯 Running in NORMAL mode.")
    img = load_image(image_source)
    if img is None: return 1
    img = resize_image(img, "Exact-fit")
    rgb = image_to_rgb_array_with_stride(img, DEFAULT_STRIDE, swap_bgr=False)
    if rgb and write_image_to_file(rgb):
        log("🎯 Image sent to projector. Ctrl+C to exit.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            cleanup()
            return 0

def run_tests(image_source):
    log("🧪 Running AUTOMATIC TESTS.")
    img = load_image(image_source)
    if img is None: return 1
    modes = [("Exact-fit", resize_image(img, "Exact-fit")),
             ("Aspect-fit", resize_image(img, "Aspect-fit"))]
    strides = [2560, 2816, 3072, 4096]
    swaps = [False, True]
    for mode_name, resized in modes:
        for stride in strides:
            for swap in swaps:
                log(f"🎯 Testing: stride={stride}, swap_bgr={swap}, mode={mode_name}")
                rgb = image_to_rgb_array_with_stride(resized, stride, swap)
                if rgb and write_image_to_file(rgb):
                    log("🔎 Observe the projector.")
                    time.sleep(5)
    cleanup()

def main():
    if not check_projector_status(): return 1
    if len(sys.argv) < 2:
        log("❌ Usage: python3 show_image.py [--test] <image>")
        return 1
    if sys.argv[1] == "--test":
        if len(sys.argv) < 3:
            log("❌ Provide image path or URL for test mode.")
            return 1
        return run_tests(sys.argv[2])
    else:
        return run_normal(sys.argv[1])

if __name__ == "__main__":
    sys.exit(main())