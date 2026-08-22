import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    print("--- STARTING REAL WORLD ACCEPTANCE VALIDATION ---")
    
    print("\n1. Uploading source document...")
    files = {'file': ('manual.txt', b'Industrial AC Unit XV-2000.\nVoltage: 240V\nFeatures: Auto-defrost, Wi-Fi connected.\nColor: Gray\nWeight: 45kg', 'text/plain')}
    res_upload = requests.post(f"{BASE_URL}/uploads", files=files)
    print("Upload Status:", res_upload.status_code)
    
    print("\n2. Ingesting Product via API and running intelligence pipeline (AUTO)...")
    payload = {
        "url": "https://example.com/products/xv-2000",
        "product_name": "AC Unit XV-2000",
        "category": "Industrial HVAC",
        "ai_mode": "AUTO"
    }
    res_prod = requests.post(f"{BASE_URL}/products/from-url?auto_process=true", json=payload)
    print("Create Product Status:", res_prod.status_code)
    if res_prod.status_code != 201:
        print(res_prod.text)
        return
        
    prod_data = res_prod.json()
    product_id = prod_data["id"]
    print("Product ID:", product_id)
    print("Intelligence output successfully fetched.")
    print("Dynamic Attributes:", json.dumps(prod_data.get("dynamicAttributes", []), indent=2))
    
    print("\n3. Testing RAG Knowledge Retrieval...")
    rag_payload = {
        "query": "What are the features of the XV-2000?",
        "top_k": 3
    }
    res_rag = requests.post(f"{BASE_URL}/retrieval/search", json=rag_payload)
    print("Retrieval Status:", res_rag.status_code)
    if res_rag.status_code == 200:
        rag_data = res_rag.json()
        print(f"Found {rag_data.get('total_found', 0)} evidences.")
        if rag_data.get('evidence'):
            print("Top match:", rag_data['evidence'][0].get('content'))
            
    print("\n--- VALIDATION COMPLETE ---")

if __name__ == "__main__":
    run_test()
