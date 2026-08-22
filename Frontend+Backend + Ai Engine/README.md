# UniHack 2026 - AI-Powered Product Intelligence Platform

> **Enterprise Industrial Product Intelligence Platform Backend, AI Engine, & Knowledge Infrastructure**

---

## 🏗️ System Architecture

This repository has been fully restructured into a cohesive application tree. The final architecture relies on exactly two application domains executing synchronously:

```text
USER / FRONTEND
      ↓
FASTAPI BACKEND
      ↓
AI ENGINE (Gemini)
      ↓
KNOWLEDGE / RETRIEVAL / RESEARCH
```

### 📂 Root Directory Structure

- `ai_engine/` - AI reasoning, orchestration, and intelligence pipeline logic. Uses the `ProductIntelligencePipeline` to validate, structure, and orchestrate the Gemini models.
- `backend/` - FastAPI infrastructure, database models, background jobs, external research, retrieval, and API boundaries.
- `frontend/` - React/Vite-based UI for submitting products and observing AI enrichment.
- `tests/` - A unified test suite ensuring complete system integrity.
- `scripts/` - Administrative, reporting, and operational execution scripts (e.g. `unihack_acceptance_runner.py`).
- `tools/` - Development tools and extraction utilities (e.g. `permanent_knowledge_acquisition.py`).
- `data_storage/` - Holds SQLite DB, cache, permanent knowledge files, and Vector storage metadata.

---

## 🚀 Running the System

### 1. Backend & AI Engine Startup
1. Ensure your Python environment is set up and activated.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables in `.env` (copied from `.env.example`).
4. Start the FastAPI server:
   ```bash
   python -m uvicorn backend.main:app --port 8000
   ```

### 2. Frontend Startup
1. Navigate to the `frontend/` directory.
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```

### 3. Automated MOCK Acceptance Tests
To safely verify system integration without consuming Gemini quota:
```bash
python scripts/unihack_acceptance_runner.py
```
