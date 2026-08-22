import asyncio
import os
import httpx
import json

async def test_ollama(prompt, format_json=True):
    payload = {
        "model": "qwen3.5:9b-q4_K_M",
        "prompt": prompt,
        "stream": False,
        "temperature": 0.1,
        "options": {
            "num_ctx": 2048
        }
    }
    if format_json:
        payload["format"] = "json"
        
    async with httpx.AsyncClient(timeout=180) as client:
        res = await client.post("http://127.0.0.1:11434/api/generate", json=payload)
        res.raise_for_status()
        return res.json()["response"]

async def main():
    p1 = "Respond with JSON containing key 'hello' and value 'world'.\n\n{"
    
    try:
        print("Test 1 WITH format=json and { prefix")
        out = await test_ollama(p1, True)
        print(f"Output:\n{repr(out)}")
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
