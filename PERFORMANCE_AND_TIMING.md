# Performance and Timing

UniHack's architecture balances accuracy, privacy, and speed. Because the system utilizes local AI inference and deterministic validation, performance characteristics are distinct from traditional web applications.

This document outlines the strictly evidence-based observations of UniHack's performance.

## Why the Demo May Take Approximately 60 Minutes
Unlike cloud APIs that stream responses instantly, UniHack in **LOCAL mode** relies on a local installation of Ollama running `qwen3.5:9b-q4_K_M`.

1. **Hardware Dependency:** Inference speed is entirely dependent on the host machine's hardware (CPU vs. GPU split).
2. **Deep Reasoning Overhead:** The models are heavily instruction-tuned to "think" before they answer. The model often generates 1000–2000 tokens of internal monologue before outputting the required JSON payload.
3. **Multi-Agent Architecture:** A single product run requires multiple sequential LLM calls (e.g., Discovery Agent, then Intelligence Agent).

## Timing Characteristics
Based on rigorous forensic logging during development and final testing on constrained hardware, the system's runtime can be categorized as follows:

- **OBSERVED:** Individual generative passes (e.g., Discovery Agent inference) were observed taking several minutes each to generate ~1500+ tokens of thought and JSON.
- **MEASURED:** The final wall-clock duration of the successful Schneider run, including all pipeline initialization, job queueing, and end-to-end processing, was exactly **60 minutes and 31 seconds** (Created: 2026-08-23 05:24:27, Completed: 2026-08-23 06:24:58).
- **EXPECTED:** Processing times will heavily scale based on hardware.
- **ESTIMATED:** High-end dedicated GPUs may reduce total runtime significantly, but on standard development hardware, expect up to an hour per product.

*Note: These are measured observations on standard developer hardware. High-end GPUs will significantly reduce these durations.*

## What We Deliberately Did NOT Hide
- We did not implement "fake loading bars" that finish in 10 seconds.
- We did not swap the 9B local model for a tiny, inaccurate 1B model just to make the demo faster.
- We did not hardcode the AI responses.

The slow processing time is the honest reality of running complex autonomous AI agent architectures entirely locally.

## What a Judge Should Do While Processing
When you submit a product for processing during the demo:
1. Do not refresh the page.
2. Note the "Processing" state.
3. This is a great time to review the `ARCHITECTURE_DEEP_DIVE.md` or `ENGINEERING_JOURNEY.md` documents while the local AI grinds through its reasoning.
4. You can open a terminal and run `ollama ps` to watch the model actively consuming CPU/GPU resources in real-time, proving the system is actively working locally.
