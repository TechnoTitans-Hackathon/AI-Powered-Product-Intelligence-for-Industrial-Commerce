import urllib.request
import json
import time
import sys

URL = 'http://127.0.0.1:11434/api/generate'
MODEL = 'qwen3.5:9b-q4_K_M'

def query_ollama(prompt, keep_alive='5m', format=None):
    payload = {
        'model': MODEL,
        'prompt': prompt,
        'keep_alive': keep_alive,
        'options': {'num_ctx': 2048, 'num_gpu': 20}
    }
    if format:
        payload['format'] = format
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers={'Content-Type': 'application/json'})
    
    start = time.time()
    try:
        with urllib.request.urlopen(req) as res:
            resp = json.loads(res.read().decode())
            dur = time.time() - start
            print(f"Success in {dur:.2f}s: {resp['response'][:50]}...")
            return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

print('1. Loading model / short inference 1')
query_ollama('Hello')
print('2. short inference 2')
query_ollama('Hi again')
print('3. short inference 3')
query_ollama('What is 2+2?')
print('4. planner-style inference')
query_ollama('You are a planner. Outline a 3 step plan to learn python.')
print('5. structured JSON inference')
query_ollama('Return a JSON object with name: John and age: 30', format='json')
print('6. Unloading model')
query_ollama('Unload', keep_alive=0)
time.sleep(2)
print('7. reload model / inference')
query_ollama('Are you there?')
print('8. Unload again')
query_ollama('Unload again', keep_alive=0)
time.sleep(2)
print('9. reload again / inference')
query_ollama('Final check')
