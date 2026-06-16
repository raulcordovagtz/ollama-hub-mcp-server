#!/usr/bin/env python3
import time
import base64
import requests
import sys
from io import BytesIO
from PIL import Image

SERVER_URL = "http://localhost:8000"
RESOLUTIONS = [512, 720, 1024]

def resize_image(img, target_height):
    aspect = img.width / img.height
    new_w = int(target_height * aspect)
    return img.resize((new_w, target_height))

def run_benchmark(image_path):
    try:
        original_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    print(f"Loaded image: {image_path} ({original_img.size})")
    
    # Warm-up
    print("\nWarming up server (256px)...")
    warm_img = resize_image(original_img, 256)
    buffered = BytesIO()
    warm_img.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    payload = {"image_base64": img_str, "prompt": "Identify.", "session_id": "benchmark_warmup"}
    try:
        requests.post(f"{SERVER_URL}/api/interact", json=payload, timeout=300)
    except Exception as e:
        print(f"Warm-up failed: {e}")
        return

    print("\nStarting Benchmarks...")
    results = {}

    for res in RESOLUTIONS:
        print(f"Testing Resolution: Height={res}px")
        
        # Resize
        start_resize = time.time()
        test_img = resize_image(original_img, res)
        # Encode
        buffered = BytesIO()
        test_img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Payload
        payload = {
            "image_base64": img_str,
            "prompt": "Read the text in this image.",
            "session_id": f"bench_{res}"
        }
        
        # Request
        start_req = time.time()
        try:
            resp = requests.post(f"{SERVER_URL}/api/interact", json=payload, timeout=300)
            if resp.status_code == 200:
                end_req = time.time()
                duration = end_req - start_req
                tokens = len(resp.json().get("raw_text_output", "")) # Rough proxy for complexity
                print(f"  -> Time: {duration:.2f}s | Output Length: {tokens} chars")
                results[res] = duration
            else:
                print(f"  -> Failed: {resp.status_code} - {resp.text}")
                results[res] = -1
        except Exception as e:
            print(f"  -> Exception: {e}")
            results[res] = -1
            
    print("\n--- Summary ---")
    for res, t in results.items():
        print(f"Height {res}px: {t:.2f}s")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 benchmark_resolution.py <image_path>")
        sys.exit(1)
    
    run_benchmark(sys.argv[1])
