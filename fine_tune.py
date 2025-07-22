#!/usr/bin/env python3
"""
Fine-tune GM12U320 projector
✅ prueba negro completo
✅ prueba patrón de rayas
✅ prueba combinaciones ganadoras
✅ limpia memoria y fuerza relleno
"""

import numpy as np
from PIL import Image
import os, time, sys

OUTPUT_FILE = "/tmp/gm12u320_image.rgb"
PROJECTOR_DEVICE = "/dev/dri/card2"
BEST_COMBOS = [
    (800,600,2560,True,"Exact-fit"),
    (800,600,2560,False,"Exact-fit"),
    (640,480,2048,True,"Exact-fit"),
    (640,480,2048,False,"Exact-fit"),
    (800,600,2560,True,"Aspect-fit"),
    (800,600,2560,False,"Aspect-fit")
]


def log(msg):
    print(msg)


def generate_image(w, h, mode, pattern):
    """Genera imagen según patrón: negro, rayas, diag"""
    img = Image.new("RGB", (w,h), (0,0,0))
    if pattern == "black":
        return img

    arr = np.zeros((h,w,3), dtype=np.uint8)

    if pattern == "stripes-h":
        for y in range(h):
            color = 255 if (y//10)%2==0 else 0
            arr[y,:,:] = [color,color,color]
    elif pattern == "stripes-v":
        for x in range(w):
            color = 255 if (x//10)%2==0 else 0
            arr[:,x,:] = [color,color,color]
    elif pattern == "diagonal":
        for y in range(h):
            for x in range(w):
                if abs(x-y)<5:
                    arr[y,x,:] = [255,255,255]
    else:  # default: grey
        arr[:,:,:] = [128,128,128]

    return Image.fromarray(arr,"RGB")


def to_rgb_bytes(img, stride, swap_bgr):
    a = np.array(img, dtype=np.uint8)
    if swap_bgr:
        a = a[:,:,::-1]
    h,w,_ = a.shape
    line_bytes = w*3
    pad = stride - line_bytes

    buf = bytearray()
    for y in range(h):
        buf += a[y,:,:].tobytes()
        buf += b'\x00'*pad

    return bytes(buf)


def write_to_file(data):
    with open(OUTPUT_FILE,'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    log(f"✅ Image written to {OUTPUT_FILE}")


def test_combo(w,h,stride,swap,mode,pattern):
    log(f"\n🎯 Testing: w={w} h={h} stride={stride} swap_bgr={swap} mode={mode} pattern={pattern}")
    img = generate_image(w,h,mode=mode,pattern=pattern)
    rgb = to_rgb_bytes(img, stride, swap)
    write_to_file(rgb)
    time.sleep(3)


if __name__ == "__main__":
    if not os.path.exists(PROJECTOR_DEVICE):
        log(f"❌ Projector device {PROJECTOR_DEVICE} not found.")
        sys.exit(1)

    log("🧹 Sending full black frame to clear projector")
    black = generate_image(800,600,"Exact-fit","black")
    write_to_file(to_rgb_bytes(black, 2560, False))
    time.sleep(3)

    patterns = ["black", "stripes-h", "stripes-v", "diagonal"]

    for idx, (w,h,s,stride_swap,mode) in enumerate(BEST_COMBOS,1):
        for pat in patterns:
            test_combo(w,h,s,stride_swap,mode,pat)

    log("✅ Finished fine-tuning tests. Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Exiting and cleaning up.")
        try: os.remove(OUTPUT_FILE)
        except: pass
        sys.exit(0)