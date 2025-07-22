#!/usr/bin/env python3
"""
GM12U320 Fine-tuning Script
===========================

🔍 Probar automáticamente combinaciones de:
- Resolución (640×480, 800×600, 1024×768)
- Stride (mínimo y múltiplos de 64)
- swap_bgr (False/True)
- resize_mode (Exact-fit/Aspect-fit)

Guarda resultados en: gm12u320_finetune.log
"""

import requests, numpy as np, io, sys, os, time, datetime
from PIL import Image

LOG_FILE = "gm12u320_finetune.log"

RESOLUTIONS = [(640, 480), (800, 600), (1024, 768)]
MODES = ["Exact-fit", "Aspect-fit"]

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()}: {msg}\n")

def load_image(image_source):
    if os.path.exists(image_source):
        img = Image.open(image_source)
        log(f"📂 Loaded local image: {image_source}")
    elif image_source.startswith(('http://', 'https://')):
        r = requests.get(image_source, timeout=10)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
        log(f"📥 Downloaded image: {image_source}")
    else:
        log("❌ Invalid image source.")
        sys.exit(1)
    return img.convert("RGB")

def resize_image(img, w, h, mode):
    if mode == "Exact-fit":
        return img.resize((w, h), Image.LANCZOS)
    else:
        img_w, img_h = img.size
        ratio = min(w/img_w, h/img_h)
        new_w, new_h = int(img_w*ratio), int(img_h*ratio)
        resized = Image.new("RGB", (w,h), (0,0,0))
        tmp = img.resize((new_w, new_h), Image.LANCZOS)
        x, y = (w-new_w)//2, (h-new_h)//2
        resized.paste(tmp, (x,y))
        return resized

def compute_strides(w):
    base = w*3
    strides = []
    for mult in range(1,6):
        s = ((base + 63)//64)*64 + (mult-1)*64
        strides.append(s)
    return strides

def image_to_bytes(img, stride, swap_bgr):
    arr = np.array(img)
    if swap_bgr:
        arr = arr[:,:,::-1]
    h,w,_ = arr.shape
    line_bytes = w*3
    pad = stride - line_bytes
    buf = bytearray()
    for y in range(h):
        buf += arr[y].tobytes()
        buf += b'\x00'*pad
    return bytes(buf)

def write_image(data, path="/tmp/gm12u320_image.rgb"):
    with open(path, "wb") as f:
        f.write(data)

def run_tests(image_source):
    img = load_image(image_source)
    log("🧪 Starting fine-tune tests…")
    combinations = []
    for (w,h) in RESOLUTIONS:
        strides = compute_strides(w)
        for mode in MODES:
            resized = resize_image(img,w,h,mode)
            for stride in strides:
                for swap in [False, True]:
                    combinations.append( (w,h,stride,swap,mode,resized) )

    for idx,(w,h,stride,swap,mode,resized) in enumerate(combinations,1):
        log(f"🔷 Test {idx}: {w}x{h} stride={stride} swap_bgr={swap} mode={mode}")
        data = image_to_bytes(resized,stride,swap)
        write_image(data)
        log(f"✅ Image written: {len(data)} bytes.")
        log("⌛ Observe projector output.")
        time.sleep(5)

    log("🎯 Fine-tune tests completed.")
    print("\n✅ Finished all tests. Check gm12u320_finetune.log for details.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python3 show_image_finetune.py <image>")
        sys.exit(1)
    run_tests(sys.argv[1])