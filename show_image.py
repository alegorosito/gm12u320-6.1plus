#!/usr/bin/env python3
import json, os, sys, time, datetime, requests, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CONFIG_FILE = "gm12u320_best.json"
LOG_FILE = "gm12u320.log"
DEFAULTS = dict(width=800, height=600, stride=2560, swap_bgr=False, mode="Exact-fit")

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()}: {msg}\n")

def check_projector_status():
    log("🎥 Checking /dev/dri/card2 …")
    if not os.path.exists('/dev/dri/card2'):
        log("❌ Projector /dev/dri/card2 not found.")
        return False
    log("✅ Projector detected.")
    return True

def load_image(src):
    try:
        if os.path.exists(src):
            log(f"📂 Loading local image: {src}")
            img = Image.open(src)
        else:
            log(f"📥 Downloading: {src}")
            r = requests.get(src, timeout=10)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
        return img.convert("RGB")
    except Exception as e:
        log(f"❌ Failed to load image: {e}")
        return None

def resize_image(image, target_w, target_h, mode="Exact-fit"):
    if mode == "Exact-fit":
        resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    else:
        img_w, img_h = image.size
        target_ratio = target_w/target_h
        img_ratio = img_w/img_h
        if img_ratio > target_ratio:
            new_w, new_h = target_w, int(target_w/img_ratio)
        else:
            new_h, new_w = target_h, int(target_h*img_ratio)
        resized = Image.new("RGB", (target_w,target_h), (0,0,0))
        tmp = image.resize((new_w,new_h), Image.Resampling.LANCZOS)
        x = (target_w-new_w)//2
        y = (target_h-new_h)//2
        resized.paste(tmp,(x,y))
    log(f"✅ Resized to {target_w}x{target_h} mode={mode}")
    return resized

def image_to_rgb_array_with_stride(img, stride, swap_bgr=False):
    a = np.array(img, dtype=np.uint8)
    if swap_bgr:
        a = a[:,:,::-1]
    h,w,_ = a.shape
    line_bytes = w*3
    pad = stride-line_bytes
    b = bytearray()
    for y in range(h):
        b += a[y,:,:].tobytes()
        b += b'\x00'*pad
    return bytes(b)

def write_image_to_file(rgb, fn="/tmp/gm12u320_image.rgb"):
    try:
        with open(fn, 'wb') as f:
            f.write(rgb)
            f.flush()
            os.fsync(f.fileno())
        log(f"✅ Written image to {fn}")
        return True
    except Exception as e:
        log(f"❌ Failed to write image: {e}")
        return False

def cleanup():
    try:
        os.remove("/tmp/gm12u320_image.rgb")
        log("🧹 Removed tmp file")
    except:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        log(f"ℹ️ Loaded config from {CONFIG_FILE}: {cfg}")
        return cfg
    log(f"⚠️ No config found, using defaults: {DEFAULTS}")
    return DEFAULTS

def main(image_path):
    if not check_projector_status(): return 1

    cfg = load_config()
    img = load_image(image_path)
    if img is None: return 1

    resized = resize_image(img, cfg["width"], cfg["height"], cfg["mode"])
    rgb = image_to_rgb_array_with_stride(resized, cfg["stride"], cfg["swap_bgr"])

    if rgb and write_image_to_file(rgb):
        log("🎯 Image sent to projector. Ctrl+C to exit.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            cleanup()
            return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 show_image.py <image>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))