# Model Licenses

This document outlines the licensing terms and requirements for the AI models used by the UniHack project.

## Qwen 3.5 (9B)
- **Purpose**: Local fallback LLM for privacy-first, on-device product intelligence inference.
- **Provider/Runtime**: Executed locally via Ollama.
- **Source**: Alibaba Cloud / Qwen Team
- **License**: Tongyi Qianwen LICENSE AGREEMENT
- **Redistribution Status**: The model binaries (`.gguf` files) are NOT distributed within this repository due to their massive size and to comply with distribution boundaries.
- **Download Instructions**: Run `ollama run qwen3.5:9b` locally to acquire the weights.

## GPT-OSS (via FreeLLMAPI)
- **Purpose**: External advanced intelligence processing.
- **Provider/Runtime**: Upstream LLM providers (routed through the local FreeLLMAPI proxy).
- **Source**: Various upstream providers (e.g., OpenAI, Anthropic, Google).
- **License**: Dependent on the upstream provider's Terms of Service for API consumption.
- **Redistribution Status**: N/A (Cloud-based API).
- **Credential Requirement**: Requires an active API key or a valid unified FreeLLMAPI token.

## Vector Embedding Models
- **Purpose**: Semantic embedding for RAG document retrieval.
- **Provider/Runtime**: Local SentenceTransformers (e.g., `all-MiniLM-L6-v2`) or similar fallback models.
- **Source**: Hugging Face / SBERT.net
- **License**: Apache 2.0
- **Redistribution Status**: Weights are downloaded automatically at runtime by the backend and cached locally. They are NOT stored in this repository.
