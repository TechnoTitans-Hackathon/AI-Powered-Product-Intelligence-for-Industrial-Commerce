# Limitations

While the UniHack Industrial Intelligence platform is fully functional, it has the following real-world limitations:

## Hardware / GPU / VRAM
- Local inference using `qwen3.5:9b` or embedding generation via FAISS/SentenceTransformers requires significant RAM and ideally an NVIDIA GPU with at least 8-12 GB of VRAM. Running locally on CPU-only machines will result in extremely slow latency.

## External API Dependencies
- If local execution is bypassed, the system falls back to external APIs routed via FreeLLMAPI (e.g. OpenAI/Google models). In this mode, the system is fully dependent on network connectivity and upstream API rate limits.
- Valid API keys are required for external routing.

## Video Processing
- Video processing is heavily constrained by disk I/O and CPU performance. FFmpeg extracts frames linearly; attempting to process videos larger than 50 MB or longer than a few minutes may timeout the backend API response window. 

## File Size Limits
- Large PDFs (e.g., hundreds of pages) will take a considerable amount of time to embed locally. We recommend testing with documents under 100 pages.

## Windows / Cross-Platform
- The codebase relies heavily on local Windows paths and FFmpeg binaries available in the path. Running the system seamlessly on Linux/macOS might require adjustments to shell subprocess commands and absolute path handling.
