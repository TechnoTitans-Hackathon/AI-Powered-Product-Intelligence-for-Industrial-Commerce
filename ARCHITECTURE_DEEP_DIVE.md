# Architecture Deep Dive

UniHack implements a highly structured, multi-stage pipeline combining the flexibility of Large Language Models (LLMs) with the rigidity of deterministic rule engines.

## Conceptual Flow
User
↓
React/Vite Frontend
↓
FastAPI API
↓
Job Service
↓
AI Processing Policy
↓
AI Engine
↓
Discovery
↓
Evidence Retrieval
↓
Knowledge Decision
↓
Research when allowed/needed
↓
Agent 2 when required
↓
Normalization
↓
Deterministic Validation
↓
Confidence
↓
Commerce Schema
↓
Explainable Result

---

### 1. React/Vite Frontend
- **Purpose:** Provide the user interface for inputting product details, tracking job status, and reviewing the final extracted data.
- **Inputs:** User text input (Brand, MPN, Category) and processing mode (LOCAL, AUTO).
- **Outputs:** API requests to the backend.

### 2. FastAPI API & Job Service
- **Purpose:** Accept requests, create asynchronous jobs, and manage state in the database.
- **Persistence:** Jobs are saved in the database with states (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
- **Failure Behavior:** If the AI Engine crashes, the Job Service catches the exception, marks the job as `FAILED`, and logs the error, preventing the API from hanging.

### 3. AI Processing Policy & Routing
- **Purpose:** Determine which AI provider and model to use based on the user's selected mode.
- **Logic:** `LOCAL` strictly forces `OllamaProvider`. `AUTO` uses deterministic logic to route to Ollama first, falling back or escalating only if permitted.

### 4. Discovery (Agent 1)
- **Purpose:** Analyze the initial product input, identify known facts, and determine what critical specifications are missing based on the category schema.
- **AI vs Deterministic:** AI (LLM inference).
- **Provider:** Ollama (`qwen3.5:9b-q4_K_M`) in LOCAL mode.

### 5. Evidence Retrieval & Knowledge Decision
- **Purpose:** Fetch supporting documentation/chunks from local databases or external sources to fill the missing gaps identified by Discovery.
- **Knowledge Decision:** A deterministic evaluation checks if the retrieved evidence is sufficient to proceed, or if deep external research is required.

### 6. Intelligence Synthesis (Agent 2)
- **Purpose:** If evidence is sufficient, this agent reads the retrieved evidence and extracts the final, highly detailed product specifications.
- **AI vs Deterministic:** AI (LLM inference).
- **Inputs:** The original product details and the retrieved Evidence Chunks.
- **Outputs:** A raw JSON object containing the extracted specifications.

### 7. Normalization & Deterministic Validation
- **Purpose:** Map the raw AI JSON output into our strict internal models and rigorously validate the claims against the evidence.
- **AI vs Deterministic:** Strictly Deterministic.
- **Validation:** The engine checks if each extracted field is `DIRECTLY_SUPPORTED`, `INFERRED`, `MISSING`, or in `CONFLICT` with the evidence.

### 8. Confidence & Commerce Schema
- **Purpose:** Assign final confidence scores based on validation results and map the data into the final 252-column industrial commerce schema.
- **Output:** An explainable, commerce-ready result delivered back to the frontend, complete with provenance tracking for every field.
