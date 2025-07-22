# fine_tune.py

import requests, numpy as np, io, time, sys, os, datetime
from PIL import Image

PROJECTOR_BYTES_PER_PIXEL = 3
LOG_FILE = "gm12u320_finetune.log"
DEFAULT_DEVICE = "/tmp/gm12u320_image.rgb"

BEST_CONFIGS = [
    {"w":800,"h":600,"stride":2560,"swap":True,"mode":"Exact-fit"},
    {"w":640,"h":480,"stride":2048,"swap":True,"mode":"Exact-fit"},
    {"w":800,"h":600,"stride":2560,"swap":False,"mode":"Exact-fit"},
    {"w":800,"h":600,"stride":2816,"swap":True,"mode":"Exact-fit"},
]

STRIDE_FACTORS = [0.8, 0.9, 1.0, 1.1, 1.2]
RES_OFFSETS = [-100, 0, 100]


def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()}: {msg}\n")


def load_image(src):
    try:
        if os.path.exists(src):
            log(f"📂 Local image: {src}")
            return Image.open(src)
        elif src.startswith(('http://','https://')):
            log(f"📥 Downloading image: {src}")
            r = requests.get(src, timeout=10)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content))
        else:
            log(f"❌ Invalid image: {src}")
            return None
    except Exception as e:
        log(f"❌ Error loading image: {e}")
        return None


def resize_image(img, w, h, mode):
    if mode == "Exact-fit":
        return img.resize((w,h), Image.Resampling.LANCZOS)
    else:
        aspect = img.width/img.height
        target_aspect = w/h
        if aspect > target_aspect:
            nw = w
            nh = int(w/aspect)
        else:
            nh = h
            nw = int(h*aspect)
        out = Image.new("RGB", (w,h), (0,0,0))
        tmp = img.resize((nw,nh), Image.Resampling.LANCZOS)
        out.paste(tmp, ((w-nw)//2, (h-nh)//2))
        return out


def image_to_rgb_array_with_stride(img, stride, swap):
    if img.mode != 'RGB':
        img = img.convert('RGB')
    arr = np.array(img)
    if swap:
        arr = arr[:,:,::-1]
    h,w,_ = arr.shape
    line_bytes = w*3
    pad = stride-line_bytes if stride>line_bytes else 0
    buf = bytearray()
    for y in range(h):
        buf += arr[y,:,:].tobytes()
        buf += b'\x00'*pad
    return bytes(buf)


def write_image_to_file(rgb, path=DEFAULT_DEVICE):
    with open(path,"wb") as f:
        f.write(rgb)
        f.flush()
        os.fsync(f.fileno())


def cleanup():
    try:
        os.remove(DEFAULT_DEVICE)
        log("🧹 Removed temp image file.")
    except:
        pass


def check_projector():
    if not os.path.exists('/dev/dri/card2'):
        log("❌ Projector /dev/dri/card2 not found.")
        return False
    log("✅ Projector detected.")
    return True


if __name__ == "__main__":

    if len(sys.argv)<2:
        print("Usage: python3 fine_tune.py <image>")
        sys.exit(1)

    if not check_projector():
        sys.exit(1)

    img = load_image(sys.argv[1])
    if img is None:
        sys.exit(1)

    idx = 1

    for base in BEST_CONFIGS:
        for sf in STRIDE_FACTORS:
            for dx in RES_OFFSETS:
                for dy in RES_OFFSETS:
                    w = max(100, base["w"]+dx)
                    h = max(100, base["h"]+dy)
                    stride = int(base["stride"]*sf)
                    swap = base["swap"]
                    mode = base["mode"]

                    log(f"[{idx}] Testing w={w} h={h} stride={stride} swap={swap} mode={mode}")

                    resized = resize_image(img,w,h,mode)
                    rgb = image_to_rgb_array_with_stride(resized,stride,swap)
                    if rgb:
                        write_image_to_file(rgb)
                        log("🔎 Observe projector.")
                        time.sleep(5)
                    idx+=1

    cleanup()
    log("✅ Fine-tune tests complete.")
    print("✅ Done. Review log in gm12u320_finetune.log")