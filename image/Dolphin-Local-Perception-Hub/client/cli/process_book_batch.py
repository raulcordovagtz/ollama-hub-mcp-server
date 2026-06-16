#!/usr/bin/env python3
import os
import sys
import math
import time
import base64
import json
import requests
from io import BytesIO
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

# Configuration
SERVER_URL = "http://localhost:8000"
c = 512 # Target height per page (Total grid height ~1024 optimized for speed/children's books)
GRID_SIZE = 2 # 2x2
BATCH_SIZE = GRID_SIZE * GRID_SIZE

def check_server():
    """Ensures server is ready."""
    print("Checking server status...")
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        if response.status_code == 200 and response.json().get("status") == "READY":
            return True
    except:
        pass
    
    print("Server not ready. Attempting to wake up...")
    # This assumes we are in client/cli and server is at ../../
    # Using the same logic as shell script would be ideal, but for Python:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cmd = f"cd {project_root} && nohup python3 -m server.server > server.log 2>&1 &"
    os.system(cmd)
    
    for _ in range(30):
        time.sleep(2)
        try:
            response = requests.get(f"{SERVER_URL}/health", timeout=2)
            if response.status_code == 200 and response.json().get("status") == "READY":
                print("Server is READY.")
                return True
        except:
            print("Waiting for server...")
    return False

def create_grid_image(pages, batch_index):
    """Stitches up to 4 pages into a 2x2 grid."""
    # Resize pages to target height
    resized_pages = []
    for p in pages:
        aspect = p.width / p.height
        new_w = int(c * aspect)
        resized_pages.append(p.resize((new_w, c)))
    
    # Calculate grid dimensions
    row_w = max(p.width for p in resized_pages) * 2
    row_h = c * 2
    
    grid = Image.new('RGB', (row_w, row_h), (255, 255, 255))
    
    # Paste pages
    # 0 | 1
    # -----
    # 2 | 3
    positions = [
        (0, 0), (resized_pages[0].width, 0),
        (0, c), (resized_pages[0].width, c) # Simplified: assuming roughly same width
    ]
    
    # robust placement
    max_w_col1 = max(resized_pages[0].width if len(resized_pages)>0 else 0, resized_pages[2].width if len(resized_pages)>2 else 0)
    
    positions = [
        (0, 0), (max_w_col1, 0),
        (0, c), (max_w_col1, c)
    ]

    for i, page in enumerate(resized_pages):
        if i >= 4: break
        grid.paste(page, positions[i])
        
        # Optional: Add clear page number overlay for the model?
        # Qwen2.5-VL is spatial, but visual cues help.
        # Let's trust the model's spatial reasoning for now as per "simple" requirements.

    return grid

def process_book(pdf_path, output_path):
    if not check_server():
        print("Error: Could not start/connect to server.")
        return

    print(f"Reading PDF: {pdf_path}")
    # Convert all pages (might be heavy for huge books, but for 30MB 72pg is fine)
    try:
        pages = convert_from_path(pdf_path)
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return

    total_pages = len(pages)
    print(f"Total Pages: {total_pages}")
    
    # Prepare Output
    existing_content = ""
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing_content = f.read()
    else:
        with open(output_path, "w") as f:
            f.write(f"# Book Analysis: {os.path.basename(pdf_path)}\n\n")

    batches = math.ceil(total_pages / BATCH_SIZE)
    
    for i in range(batches):
        batch_label = f"## Batch {i+1} "
        if batch_label in existing_content:
            print(f"Skipping Batch {i+1} (Already processed).")
            continue

        start_idx = i * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_pages)
        batch_pages = pages[start_idx:end_idx]
        
        print(f"Processing Batch {i+1}/{batches} (Pages {start_idx+1}-{end_idx})...")
        
        grid_img = create_grid_image(batch_pages, i)
        
        # Convert to Base64
        buffered = BytesIO()
        grid_img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Prompt
        prompt = (
            f"This image contains pages {start_idx+1} through {end_idx} of a book, arranged in a grid. "
            "Read the text content of each page in order (Top-Left, Top-Right, Bottom-Left, Bottom-Right). "
            "Output the text clearly separated by page number."
        )
        
        # Send Request
        payload = {
            "image_base64": img_str,
            "prompt": prompt,
            "session_id": f"book_{os.path.basename(pdf_path)}"
        }
        
        try:
            resp = requests.post(f"{SERVER_URL}/api/interact", json=payload, timeout=300)
            if resp.status_code == 200:
                result = resp.json()
                raw_text = result.get("raw_text_output", "")
                
                # Append to file
                with open(output_path, "a") as f:
                    f.write(f"## Batch {i+1} (Pages {start_idx+1}-{end_idx})\n\n")
                    f.write(raw_text)
                    f.write("\n\n---\n\n")
                
                print(f"Batch {i+1} Complete.")
            else:
                print(f"Error in batch {i+1}: {resp.text}")
        except Exception as e:
            print(f"Exception in batch {i+1}: {e}")

    print(f"Analysis saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_book_batch.py <pdf_path>")
        sys.exit(1)
    
    pdf_in = sys.argv[1]
    
    # Auto-name output
    base = os.path.splitext(os.path.basename(pdf_in))[0]
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "server/image/outputs/Dolphin-Perception") 
    # Hardcoded path based on project structure for now, or use relative
    out_dir = "/Users/crotalo/desarrollo-local/server/image/outputs/Dolphin-Perception"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    out_file = os.path.join(out_dir, f"{base}_full_analysis.md")
    
    process_book(pdf_in, out_file)
