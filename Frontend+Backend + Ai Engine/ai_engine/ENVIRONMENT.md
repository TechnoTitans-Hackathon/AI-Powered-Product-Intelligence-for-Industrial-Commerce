# AI Intelligence Engine - Environment Setup

## Prerequisites

- **Python:** 3.10+
- **OS:** Windows / Linux / macOS
- **Environment:** A virtual environment is highly recommended.

## Standalone Development Setup

Because the database and backend components are not yet built, the AI Engine uses mock providers to allow for uninterrupted development and testing. 

1. **Clone/Navigate to the repository:**
   ```bash
   cd d:\Hackathon\ai_engine
   ```

2. **Install dependencies:**
   No external `requirements.txt` is provided for the core engine because it only relies on `pydantic` and standard library modules (`asyncio`, `time`, `json`, `uuid`, `logging`).
   ```bash
   pip install pydantic pytest pytest-asyncio
   ```

3. **Verify Installation:**
   Run the test suite to ensure the environment is configured correctly.
   ```bash
   python -m pytest tests/test_engine.py -v
   ```

## Production Integration (Future)

When integrating this standalone engine into the final product:
1. Provide concrete implementations for `AIProviderInterface`, `RetrieverInterface`, and `ResearchInterface`.
2. Connect the `CommerceOutputAdapter` JSON/CSV output to the ingestion API of the commerce platform.
3. Replace `TemporaryKnowledgeStore` with a persistent Redis/Database backed storage solution while maintaining the 4GB / 7-day retention constraints.
