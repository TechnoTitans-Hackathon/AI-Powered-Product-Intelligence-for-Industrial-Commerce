import os
import sys
import time
import requests
import asyncio
from dotenv import load_dotenv

workspace_root = r"D:\Hackathon\Frontend+Backend + Ai Engine"
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

load_dotenv(os.path.join(workspace_root, ".env"))

API_URL = "http://localhost:8000/api/v1"

def wait_for_backend():
    print("Waiting for backend to be ready...")
    for _ in range(30):
        try:
            res = requests.get("http://localhost:8000/api/v1/health")
            if res.status_code == 200:
                print("Backend is ready.")
                return True
        except:
            pass
        time.sleep(1)
    print("Backend failed to become ready.")
    return False

def test_ollama():
    print("Testing Ollama runtime...")
    try:
        res = requests.get("http://127.0.0.1:11434/api/tags")
        res.raise_for_status()
        tags = res.json()
        model_exists = any(m["name"] == "qwen3.5:9b-q4_K_M" for m in tags.get("models", []))
        if model_exists:
            print("Ollama test: PASS (model qwen3.5:9b-q4_K_M found)")
            return True
        else:
            print("Ollama test: FAIL (model missing)")
            return False
    except Exception as e:
        print(f"Ollama test: FAIL ({e})")
        return False

def test_multimodal_e2e():
    print("\n--- Starting Multimodal E2E Tests ---")
    inputs = {
        "text": ("test.txt", b"This is a test document with specs: 10V, 5A."),
        "image": ("test.jpg", b"fake image bytes"),
        "pdf": ("test.pdf", b"%PDF-1.4 dummy pdf"),
        "video": ("test.mp4", b"fake video bytes")
    }

    for modality, (filename, content) in inputs.items():
        print(f"Testing {modality.upper()}...")
        # 1. Create product
        prod_res = requests.post(f"{API_URL}/products", json={
            "name": f"Test {modality}",
            "description": f"{modality} based product"
        }, headers={"tenant-id": "default"})
        
        if prod_res.status_code != 201:
            print(f"  FAIL: Could not create product. {prod_res.text}")
            continue
            
        product_id = prod_res.json()["id"]
        
        # 2. Upload file
        files = {'file': (filename, content, "application/octet-stream")}
        data = {'product_id': product_id}
        upload_res = requests.post(f"{API_URL}/uploads", files=files, data=data, headers={"tenant-id": "default"})
        if upload_res.status_code != 201:
            print(f"  FAIL: Could not upload file. {upload_res.text}")
            continue
            
        print("  Upload successful, processing...")
        
        # 3. Process
        process_res = requests.post(f"{API_URL}/products/{product_id}/process", headers={"tenant-id": "default"})
        if process_res.status_code != 202:
            print(f"  FAIL: Could not start processing. {process_res.text}")
            continue
            
        job_id = process_res.json()["job_id"]
        
        # 4. Wait for completion
        completed = False
        for _ in range(60):
            job_status = requests.get(f"{API_URL}/jobs/{job_id}", headers={"tenant-id": "default"})
            if job_status.status_code == 200:
                js = job_status.json()
                if js["status"] == "COMPLETED":
                    completed = True
                    break
                elif js["status"] == "FAILED":
                    print(f"  FAIL: Job failed.")
                    break
            time.sleep(2)
            
        if completed:
            print(f"  PASS: {modality.upper()} processed successfully.")
        else:
            print(f"  FAIL: {modality.upper()} processing timed out.")

    print("\nTesting YOUTUBE URL...")
    url_res = requests.post(f"{API_URL}/products/from-url", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}, headers={"tenant-id": "default"})
    if url_res.status_code == 201:
        print("  PASS: YOUTUBE URL processed successfully.")
    else:
        print(f"  FAIL: YOUTUBE URL failed. {url_res.text}")

    print("\nTesting ARBITRARY URL...")
    url_res = requests.post(f"{API_URL}/products/from-url", json={"url": "https://example.com"}, headers={"tenant-id": "default"})
    if url_res.status_code == 201:
        print("  PASS: ARBITRARY URL processed successfully.")
    else:
        print(f"  FAIL: ARBITRARY URL failed. {url_res.text}")

if __name__ == "__main__":
    if wait_for_backend():
        test_ollama()
        test_multimodal_e2e()
