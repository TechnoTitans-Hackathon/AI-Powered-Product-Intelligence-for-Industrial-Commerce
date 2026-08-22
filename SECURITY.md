# Security, Limitations, and Authorship

## Security
- **No Secrets in Source Control**: Automated GitHub pre-push hardening scripts have verified that no hardcoded credentials (OpenAI keys, passwords, database URLs with passwords) are present in the repository.
- **Local Proxy Gateway**: The architecture uses a local proxy (`freellmapi`) to enforce that the frontend and backend do not directly need to manage external API keys for advanced model reasoning, reducing leak surface area.

## Limitations
- **Local Fallback Speed**: Using the local Ollama fallback (`qwen3.5:9b`) requires substantial VRAM and will process documents significantly slower than the primary gateway.
- **PDF Parsing Complexity**: Highly dense CAD drawings or unstructured imagery inside PDFs are currently only partially vectorized. We rely on the LLM's spatial reasoning via text coordinates where possible.
- **Production Scale**: This is a Hackathon MVP. SQLite is used for demonstration purposes. A production deployment would migrate the `data_storage` to distributed blob storage and PostgreSQL.

## Authorship & Acknowledgements
- **Project**: UniHack 2026 - AI-Powered Product Intelligence for Industrial Commerce
- **Authors**: TechnoTitans Hackathon Team
- **Acknowledgements**: We extend our thanks to the open-source community, particularly the maintainers of FastAPI, React, LangChain, Ollama, and FreeLLMAPI (Tashfeen Ahmed) for the underlying tools making this architecture possible.
