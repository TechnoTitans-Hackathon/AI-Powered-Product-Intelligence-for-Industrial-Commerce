# Limitations and Honesty

UniHack was built for accuracy and privacy, not for marketing hype. The architecture makes explicit trade-offs.

## Current Limitations

1. **Local Inference Latency:** Running a 9B parameter model on consumer hardware is slow. A single pipeline run can take approximately 60 minutes of wall-clock time because the model is generating thousands of tokens of deep reasoning and queuing multiple tasks.
2. **Hardware Dependency:** Performance scales linearly with the host's GPU/CPU capabilities.
3. **Incomplete Evidence:** The system is completely dependent on its retrieval phase. If public documentation or datasheets for a niche product cannot be found, the system will honestly return missing attributes.
4. **Rate Limits:** In `AUTO` mode, falling back to external API proxies (like FreeLLMAPI) exposes the system to HTTP 429 rate limit errors if the host is overloaded.
5. **Conflicting Evidence:** Industrial supply chains often have conflicting datasheets (e.g., v1 vs. v2 of a component). If the AI extracts a value from v1 that contradicts v2, the validation engine will flag a conflict.
6. **Model Formatting Quirks:** `qwen3.5` is highly verbose and occasionally splits its structured output across multiple JSON blocks, requiring complex deterministic parsing in our backend to reconstruct the data.
7. **One Run Does Not Prove Universal Correctness:** While our documented validation run on the Schneider Electric product was successful, B2B data is chaotic. Not every product will parse flawlessly.

## Why These Limitations Are Acceptable
In B2B commerce, a slow, highly verified, and honest record is infinitely more valuable than an instantaneous hallucination. We explicitly chose to accept a 60-minute latency in exchange for local data privacy and deep evidence-based validation. If an attribute is missing, it is better left `null` than guessed.
