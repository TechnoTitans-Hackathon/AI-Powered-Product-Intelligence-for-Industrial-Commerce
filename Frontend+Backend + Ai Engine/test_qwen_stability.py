"""
Qwen3.5:9b-q4_K_M Stability Test Suite
========================================
Graduated testing of the local Qwen3.5 runtime.
Tests model on CUDA via Ollama with increasing complexity.
"""
import httpx
import json
import time
import subprocess
import sys

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3.5:9b-q4_K_M"
TIMEOUT = 180  # seconds

results = []

def vram_snapshot():
    """Get current GPU VRAM usage."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total,utilization.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def ollama_ps():
    """Get currently loaded models."""
    try:
        r = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def run_test(test_name: str, prompt: str, num_ctx: int = 1024, num_predict: int = 32,
             temperature: float = 0, use_format: str = None, use_chat: bool = False,
             system_prompt: str = None):
    """Run a single inference test and record results."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")

    vram_before = vram_snapshot()
    print(f"VRAM before: {vram_before}")

    options = {
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "temperature": temperature,
    }

    if use_chat:
        # Use /api/chat endpoint
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if use_format:
            body["format"] = use_format
        endpoint = f"{OLLAMA_URL}/api/chat"
    else:
        # Use /api/generate endpoint
        body = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if use_format:
            body["format"] = use_format
        endpoint = f"{OLLAMA_URL}/api/generate"

    start = time.time()
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(endpoint, json=body)

        elapsed = time.time() - start
        vram_during = vram_snapshot()

        result = {
            "test": test_name,
            "status": "SUCCESS" if resp.status_code == 200 else f"HTTP_{resp.status_code}",
            "http_code": resp.status_code,
            "latency_ms": round(elapsed * 1000),
            "vram_before": vram_before,
            "vram_during": vram_during,
        }

        if resp.status_code == 200:
            data = resp.json()
            if use_chat:
                response_text = data.get("message", {}).get("content", "")
            else:
                response_text = data.get("response", "")

            result["model"] = data.get("model", "UNKNOWN")
            result["response_length"] = len(response_text)
            result["response_preview"] = response_text[:200]
            result["eval_count"] = data.get("eval_count", 0)
            result["done"] = data.get("done", False)

            # Check for valid JSON if format=json
            if use_format == "json":
                try:
                    # Qwen3.5 thinking mode: strip <think>...</think> blocks
                    clean = response_text
                    if "<think>" in clean:
                        # Find last </think> and take content after it
                        idx = clean.rfind("</think>")
                        if idx >= 0:
                            clean = clean[idx + len("</think>"):].strip()
                    parsed = json.loads(clean) if clean else None
                    result["json_valid"] = parsed is not None
                    result["json_parsed"] = parsed
                except json.JSONDecodeError as e:
                    result["json_valid"] = False
                    result["json_error"] = str(e)
        else:
            result["error"] = resp.text[:500]

        results.append(result)
        print(f"STATUS: {result['status']}")
        print(f"MODEL: {result.get('model', 'N/A')}")
        print(f"LATENCY: {result['latency_ms']}ms")
        print(f"RESPONSE LENGTH: {result.get('response_length', 'N/A')}")
        print(f"RESPONSE PREVIEW: {result.get('response_preview', 'N/A')[:120]}")
        if 'json_valid' in result:
            print(f"JSON VALID: {result['json_valid']}")
            if result.get('json_parsed'):
                print(f"JSON PARSED: {json.dumps(result['json_parsed'], indent=2)[:200]}")
        print(f"EVAL COUNT: {result.get('eval_count', 'N/A')}")
        print(f"VRAM during: {vram_during}")
        return result

    except Exception as e:
        elapsed = time.time() - start
        result = {
            "test": test_name,
            "status": "EXCEPTION",
            "error": str(e),
            "error_type": type(e).__name__,
            "latency_ms": round(elapsed * 1000),
            "vram_before": vram_before,
        }
        results.append(result)
        print(f"STATUS: EXCEPTION")
        print(f"ERROR: {e}")
        print(f"LATENCY: {result['latency_ms']}ms")
        return result


def main():
    print("=" * 60)
    print("QWEN3.5:9b-q4_K_M STABILITY TEST SUITE")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"VRAM baseline: {vram_snapshot()}")
    print(f"Ollama ps: {ollama_ps()}")
    print()

    # ─── TEST 1: Tiny plain-text generation ─────────────────────
    run_test(
        "T1_PLAIN_TEXT",
        prompt="Say hello in one sentence.",
        num_predict=32,
        temperature=0,
    )

    # ─── TEST 2: Tiny JSON generation ───────────────────────────
    run_test(
        "T2_TINY_JSON",
        prompt='Return exactly: {"ok": true}',
        num_predict=64,
        temperature=0,
        use_format="json",
    )

    # ─── TEST 3: Qwen #1 actual planner schema ─────────────────
    # Simulates what the Discovery Agent sends
    planner_prompt = """Analyze this product and provide:
1. Product Identity: manufacturer, brand, part_number, product_name, category, industry, confidence (0-1)
2. Known Information: list of {field, value} pairs
3. Missing Information: list of missing attributes
4. Research Required: true/false

Product: Vishay VS-HFA06TB60 Ultrafast Diode

Return as JSON with keys: product_identity, known_information, missing_information, research_required"""

    run_test(
        "T3_PLANNER_SCHEMA",
        prompt=planner_prompt,
        num_predict=256,
        num_ctx=2048,
        temperature=0,
        use_format="json",
    )

    # ─── TEST 4: Qwen #2 actual router schema ──────────────────
    # Simulates what the Router sends to decide agent2_required
    router_prompt = """You are a routing decision engine. Based on the evidence quality, decide if Agent 2 (deep synthesis) is required.

Evidence summary:
- 3 technical specifications found
- Confidence: 0.65
- Missing fields: 2

Respond with JSON: {"agent2_required": true/false, "reason": "brief reason", "task": {"objective": "what to do"}}"""

    run_test(
        "T4_ROUTER_SCHEMA",
        prompt=router_prompt,
        num_predict=128,
        num_ctx=2048,
        temperature=0,
        use_format="json",
        use_chat=True,
        system_prompt="You are a JSON-only routing decision engine. Return only valid JSON.",
    )

    # ─── TEST 5: Repeated inference x5 ──────────────────────────
    print(f"\n{'='*60}")
    print("TEST: T5_REPEATED_5x")
    print(f"{'='*60}")
    for i in range(5):
        r = run_test(
            f"T5_REP_{i+1}",
            prompt=f"Return JSON: {{\"iteration\": {i+1}, \"status\": \"ok\"}}",
            num_predict=64,
            temperature=0,
            use_format="json",
        )
        if r["status"] != "SUCCESS":
            print(f"REPEATED TEST FAILED at iteration {i+1}")
            break

    # ─── TEST 6: Repeated inference x10 ─────────────────────────
    print(f"\n{'='*60}")
    print("TEST: T6_REPEATED_10x")
    print(f"{'='*60}")
    for i in range(10):
        r = run_test(
            f"T6_REP_{i+1}",
            prompt=f'Return: {{"count": {i+1}}}',
            num_predict=32,
            temperature=0,
            use_format="json",
        )
        if r["status"] != "SUCCESS":
            print(f"REPEATED TEST FAILED at iteration {i+1}")
            break

    # ─── TEST 7: num_predict scaling ────────────────────────────
    for np in [32, 128, 256, 512]:
        run_test(
            f"T7_PREDICT_{np}",
            prompt="List 10 common electronic components with their typical specifications in JSON format.",
            num_predict=np,
            num_ctx=2048,
            temperature=0,
            use_format="json",
        )

    # ─── SUMMARY ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STABILITY TEST SUMMARY")
    print(f"{'='*60}")
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = sum(1 for r in results if r["status"] != "SUCCESS")
    print(f"Total:  {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        print(f"  {status_icon} {r['test']}: {r['status']} ({r['latency_ms']}ms)")
        if r["status"] != "SUCCESS" and "error" in r:
            print(f"     ERROR: {r['error'][:100]}")
        if r.get("json_valid") is False:
            print(f"     JSON ERROR: {r.get('json_error', 'unknown')[:100]}")

    print(f"\nFinal VRAM: {vram_snapshot()}")
    print(f"Final Ollama ps: {ollama_ps()}")

    # Return exit code based on results
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
