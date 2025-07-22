
#!/usr/bin/env python3

"""
GM12U320 Projector Aspect Calibration Tool
------------------------------------------

✅ Usa los mejores parámetros encontrados para color y alineación.
✅ Permite probar offsets y escalas adicionales para corregir el aspecto.
"""

import sys, os, time, io, datetime, requests
import numpy as np
from PIL import Image
from pathlib import Path

# ⚙️ configuración base
PROJECTOR_DEVICE = "/dev/dri/card2"
OUTPUT_FILE = "/tmp/gm12u320_image.rgb"
BEST_W, BEST_H = 800, 600
BEST_STRIDE = 2560
BEST_SWAP_BGR = True
BEST_MODE = "Exact-fit"

def log(msg):
    now = datetime.datetime.now()
    print(f"[{now:%H:%M:%S}] {msg}")

def load_image(image_source):
    if Path(image_source).exists():
        log(f"📂 Loading local image: {image_source}")
        return Image.open(image_source)
    if image_source.startswith(('http://', 'https://')):
        log(f"📥 Downloading image from: {image_source}")
        r = requests.get(image_source, timeout=10)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
    raise ValueError(f"Invalid image source: {image_source}")

def resize_and_crop(image, w, h, dx=0, dy=0, mode="Exact-fit"):
    """
    Redimensiona y ajusta offsets.
    dx, dy pueden ser negativos o positivos para recortar/añadir margen.
    """
    log(f"🔧 Resizing image to {w+dx}x{h+dy} (base: {w}x{h}, dx={dx}, dy={dy}, mode={mode})")
    if image.mode != 'RGB':
        image = image.convert('RGB')
    img_w, img_h = image.size

    target_w = w + dx
    target_h = h + dy

    if mode == "Exact-fit":
        resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        final_img = Image.new('RGB', (w, h), (0, 0, 0))
        x = max((w - target_w) // 2, 0)
        y = max((h - target_h) // 2, 0)
        final_img.paste(resized, (x, y))
    else:  # Aspect-fit
        ratio = img_w / img_h
        target_ratio = target_w / target_h
        if ratio > target_ratio:
            nw = target_w
            nh = int(target_w / ratio)
        else:
            nh = target_h
            nw = int(target_h * ratio)
        resized = image.resize((nw, nh), Image.Resampling.LANCZOS)
        final_img = Image.new('RGB', (w, h), (0, 0, 0))
        x = (w - nw) // 2
        y = (h - nh) // 2
        final_img.paste(resized, (x, y))
    return final_img

def image_to_bytes(image, stride, swap_bgr=False):
    arr = np.array(image, dtype=np.uint8)
    if swap_bgr:
        arr = arr[:, :, ::-1]
    h, w, _ = arr.shape
    line_bytes = w * 3
    pad = stride - line_bytes
    buf = bytearray()
    for y in range(h):
        buf.extend(arr[y].tobytes())
        buf.extend(b'\x00' * pad)
    return bytes(buf)

def write_to_projector(data):
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    log(f"✅ Image written to {OUTPUT_FILE}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} <image_path_or_url> [dx] [dy]")
        print("Example:")
        print(f"  {sys.argv[0]} image.jpg -20 10")
        sys.exit(1)

    image_source = sys.argv[1]
    dx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    dy = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if not os.path.exists(PROJECTOR_DEVICE):
        log(f"❌ Projector device {PROJECTOR_DEVICE} not found. Make sure driver is loaded.")
        sys.exit(1)

    img = load_image(image_source)
    resized = resize_and_crop(img, BEST_W, BEST_H, dx, dy, BEST_MODE)
    rgb_data = image_to_bytes(resized, BEST_STRIDE, BEST_SWAP_BGR)
    write_to_projector(rgb_data)

    log("🎯 Image sent to projector. Press Ctrl+C when done.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🧹 Exiting and cleaning up.")
        try:
            os.remove(OUTPUT_FILE)
        except:
            pass

if __name__ == "__main__":
    main()