#!/usr/bin/env python3
"""
GM12U320 Projector Image Display Script
=======================================
✅ Modo normal: muestra una imagen llenando toda la pantalla del proyector.
✅ Modo test: recorre automáticamente combinaciones de resolución / stride / bgr / escalado y detecta la más “óptima”.

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

import requests, numpy as np, io, time, sys, os, datetime
from PIL import Image

LOG_FILE = "gm12u320_test.log"
PROJECTOR_DEVICE = '/dev/dri/card2'
OUTPUT_FILE = "/tmp/gm12u320_image.rgb"

RESOLUTIONS = [
    (600, 480, 2048),
    (640, 480, 2048),
    (800, 600, 2560),
    (1024, 768, 4096),
]

best_config = {"score": float("inf"), "config": None}

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()}: {msg}\n")

def check_projector_status():
    log(f"🎥 Checking projector device {PROJECTOR_DEVICE} …")
    if not os.path.exists(PROJECTOR_DEVICE):
        log("❌ Projector device not found.")
        return False
    log("✅ Projector detected.")
    return True

def cleanup():
    try:
        os.remove(OUTPUT_FILE)
        log("🧹 Removed temporary image file.")
    except:
        pass

def load_image(src):
    try:
        if os.path.isfile(src):
            log(f"📂 Loading local image: {src}")
            img = Image.open(src).convert("RGB")
        elif src.startswith(('http', 'https')):
            log(f"📥 Downloading image: {src}")
            r = requests.get(src, timeout=10)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
        else:
            raise ValueError("Invalid image source")
        log(f"✅ Image loaded: {img.size[0]}x{img.size[1]}")
        return img
    except Exception as e:
        log(f"❌ Failed to load image: {e}")
        return None

def resize_image(image, w, h, mode):
    if mode == "Exact-fit":
        img = image.resize((w, h), Image.Resampling.LANCZOS)
        log(f"✅ Resized exact {w}x{h}")
        return img
    else:
        img_w, img_h = image.size
        target_ratio = w / h
        img_ratio = img_w / img_h
        if img_ratio > target_ratio:
            new_w = w
            new_h = int(w / img_ratio)
        else:
            new_h = h
            new_w = int(h * img_ratio)
        canvas = Image.new("RGB", (w,h), (0,0,0))
        tmp = image.resize((new_w,new_h), Image.Resampling.LANCZOS)
        x = (w-new_w)//2
        y = (h-new_h)//2
        canvas.paste(tmp, (x,y))
        log(f"✅ Resized aspect-fit {new_w}x{new_h}")
        return canvas

def image_to_rgb(image, stride, swap_bgr):
    arr = np.array(image, dtype=np.uint8)
    if swap_bgr: arr = arr[:,:,::-1]
    h,w,_ = arr.shape
    line_bytes = w*3
    pad = stride - line_bytes
    score = abs(pad)  # cuanto menor el padding, mejor
    buf = bytearray()
    for y in range(h):
        buf += arr[y,:,:].tobytes()
        if pad > 0: buf += b'\x00'*pad
    log(f"✅ Converted: stride={stride} swap_bgr={swap_bgr} pad/line={pad}")
    return bytes(buf), score

def write_image(data):
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    log(f"✅ Image written to {OUTPUT_FILE}")

def run_normal(image_source, config=None):
    log("🎯 NORMAL mode")
    img = load_image(image_source)
    if img is None: return
    if config:
        w,h,s,swap,mode = config
    else:
        w,h,s,swap,mode = 800,600,2560,False,"Exact-fit"
    img = resize_image(img,w,h,mode)
    rgb,_ = image_to_rgb(img,s,swap)
    write_image(rgb)
    log(f"🎯 Displaying {w}x{h} stride={s} swap_bgr={swap} mode={mode}… Ctrl+C to exit")
    try: 
        while True: time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

def run_tests(image_source):
    global best_config
    log("🧪 TEST mode")
    img = load_image(image_source)
    if img is None: return
    modes = ["Exact-fit","Aspect-fit"]
    swaps = [False,True]
    for w,h,s in RESOLUTIONS:
        for mode in modes:
            resized = resize_image(img,w,h,mode)
            for swap in swaps:
                log(f"🎯 Testing: {w}x{h} stride={s} swap_bgr={swap} mode={mode}")
                rgb,score = image_to_rgb(resized,s,swap)
                write_image(rgb)
                log(f"🔎 Observe output. Waiting 3s…")
                if score < best_config["score"]:
                    best_config = {
                        "score": score,
                        "config": (w,h,s,swap,mode)
                    }
                time.sleep(3)
    cleanup()
    best = best_config["config"]
    if best:
        log(f"✅ Best configuration detected: {best}")
        print(f"\n🎯 Best detected: Resolution={best[0]}x{best[1]} Stride={best[2]} Swap_BGR={best[3]} Mode={best[4]}")
        print(f"Run normally with:\n  sudo python3 show_image.py <image>")

def main():
    if not check_projector_status(): return
    if len(sys.argv) < 2:
        log("❌ Usage: python3 show_image.py [--test] <image>")
        return
    if sys.argv[1] == "--test":
        if len(sys.argv)<3:
            log("❌ Provide image path or URL for test.")
            return
        run_tests(sys.argv[2])
    else:
        run_normal(sys.argv[1])

if __name__ == "__main__":
    main()