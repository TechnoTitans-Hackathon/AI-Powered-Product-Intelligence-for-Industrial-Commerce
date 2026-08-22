# Architecture

## High-Level System Design
The platform consists of four major components:
1. **Frontend (React/Vite)**: A dynamic interface for uploading documents and visualizing AI-extracted structured intelligence.
2. **Backend (FastAPI)**: Serves API endpoints, orchestrates data ingestion (PDFs via `PyMuPDF`, URLs via `BeautifulSoup`), and manages SQLite database state.
3. **AI Orchestration (LangChain/Pydantic)**: Uses a dual-agent validation model where Agent 1 proposes an extraction, and Agent 2 critiques/validates it.
4. **Model Providers**: 
   - Primary: `FreeLLMAPI` Gateway running locally (`http://localhost:3001`).
   - Fallback/Planner: `Ollama` running locally (`http://127.0.0.1:11434`).

## Data Flow
```mermaid
graph TD
    A[User UI] -->|Uploads PDF/URL| B(FastAPI Backend)
    B -->|Extracts Text & Vectors| C[Vector Store]
    B -->|Context + Prompt| D(AI Engine / LangChain)
    D -->|Calls| E[FreeLLMAPI (gpt-oss-120b)]
    D -->|Fallback Calls| F[Ollama (qwen3.5:9b)]
    D -->|Returns Pydantic JSON| B
    B -->|Persists Data| G[(SQLite)]
    B -->|JSON Response| A
```
