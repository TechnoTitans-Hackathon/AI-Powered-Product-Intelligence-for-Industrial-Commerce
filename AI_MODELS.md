# AI Models Strategy

## Model Ecosystem
To ensure stability and high-quality structured output, the UniHack AI engine supports two primary paradigms:

### 1. FreeLLMAPI Proxy (Primary)
- **Model**: `gpt-oss-120b` (routed via local `freellmapi` on port 3001)
- **Purpose**: Used for high-complexity JSON structuring, zero-shot entity extraction, and multi-agent critique validation. It handles large context windows and produces highly reliable Pydantic validation outputs.
- **Reproducibility**: The proxy runs locally and handles external connectivity transparently without hardcoding secrets in the codebase.

### 2. Ollama Local Fallback (Secondary)
- **Model**: `qwen3.5:9b-q4_K_M`
- **Purpose**: Designed as an air-gapped, fully local planner. Used when external gateways are down or for preprocessing tasks.
- **Reproducibility**: Due to the massive size of `.gguf` binaries, Ollama models are explicitly excluded from Git. 
- **Setup Instruction**: Run `ollama pull qwen3.5:9b` locally before running the backend if you wish to use the local fallback agent.
