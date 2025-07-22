#!/usr/bin/env python3
import json, sys, time, os
from show_image import (
    load_image, resize_image, image_to_rgb_array_with_stride,
    write_image_to_file, cleanup, log, check_projector_status
)

CONFIG_FILE = "gm12u320_best.json"

def calibration(image_path):
    if not check_projector_status(): return 1

    img = load_image(image_path)
    if img is None: return 1

    log("🧪 Running CALIBRATION")
    modes = [("Exact-fit",), ("Aspect-fit",)]
    strides = [2048, 2560, 2816, 3072]
    swaps = [False, True]
    resolutions = [(640,480), (720,480), (800,600)]

    results = []
    idx = 1

    for w,h in resolutions:
        for mode_name in modes:
            for stride in strides:
                for swap in swaps:
                    log(f"\n[{idx}] Testing: {w}x{h} stride={stride} swap_bgr={swap} mode={mode_name[0]}")
                    resized = resize_image(img, w, h, mode_name[0])
                    rgb = image_to_rgb_array_with_stride(resized, stride, swap)
                    if rgb and write_image_to_file(rgb):
                        log("🔎 Observe the projector.")
                        time.sleep(3)
                        results.append( (idx, w,h,stride,swap,mode_name[0]) )
                    idx +=1

    cleanup()

    print("\n📝 Calibration finished. Choose the number of the best result:")
    for r in results:
        print(f"{r[0]}: {r[1]}x{r[2]} stride={r[3]} swap_bgr={r[4]} mode={r[5]}")

    choice = int(input("➡️ Enter choice number: "))
    best = next(r for r in results if r[0] == choice)

    config = {
        "width": best[1],
        "height": best[2],
        "stride": best[3],
        "swap_bgr": best[4],
        "mode": best[5]
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    log(f"✅ Saved best config to {CONFIG_FILE}: {config}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 calibration.py <image>")
        sys.exit(1)
    sys.exit(calibration(sys.argv[1]))