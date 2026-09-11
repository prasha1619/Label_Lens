import os
import sys
import zipfile
import httpx

model_dir = os.path.expanduser(r"~\.EasyOCR\model")
os.makedirs(model_dir, exist_ok=True)

models = {
    "craft_mlt_25k.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
    "english_g2.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

client = httpx.Client(follow_redirects=True, timeout=120.0, headers=headers)

for model_name, url in models.items():
    dest_path = os.path.join(model_dir, model_name)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000000:
        print(f"[OK] {model_name} already exists ({os.path.getsize(dest_path)} bytes)")
        continue
    
    zip_path = os.path.join(model_dir, f"temp_{model_name}.zip")
    print(f"Downloading {model_name} from {url}...")
    
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=65536):
                f.write(chunk)
                
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(model_dir)
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    print(f"[SUCCESS] {model_name} installed successfully!")

print("All EasyOCR models downloaded and ready!")
