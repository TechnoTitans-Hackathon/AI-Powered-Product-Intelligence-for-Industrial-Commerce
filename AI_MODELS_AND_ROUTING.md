# AI Models and Routing

UniHack features a dynamic, policy-driven AI routing architecture that separates deterministic business logic from probabilistic AI inference.

## The Modes
Users select a processing mode which dictates the AI provider and model routing.

### 1. LOCAL
- **Provider:** Ollama
- **Model:** `qwen3.5:9b-q4_K_M`
- **External Access:** Strictly prohibited.
- **Intended Role:** Maximum privacy. Ensures proprietary supply chain data never leaves the host machine.
- **Judge Recommendation:** Use this for the demonstration to prove the system works entirely offline and autonomously.

### 2. AUTO / FAST / DEEP
- **Intended Role:** These modes are architecturally designed to scale up to frontier models (like GPT-4o or Gemini) via the FreeLLMAPI proxy when deeper reasoning or faster inference is required.
- **Fallback Behavior:** If external APIs are unavailable or rate-limited, deterministic routing logic safely falls back to local models where applicable.

## Deterministic Routing
UniHack uses a deterministic `Pipeline` orchestrator, completely eliminating the latency and unreliability of an LLM-based router. The pipeline explicitly inspects the requested mode and current environmental capabilities to assign exactly which provider handles Agent 1 (Discovery) and Agent 2 (Intelligence).

## The Qwen3.5 Implementation
The system is explicitly tuned for `qwen3.5:9b-q4_K_M`.
- **Reasoning Overload:** This model is highly instruction-tuned to generate extensive "Thinking Processes" before delivering answers.
- **JSON Parser Hardening:** We built a custom, robust token-stream scanner using `json.JSONDecoder().raw_decode()`. Instead of relying on brittle string splitting or standard `json.loads()`, our parser iteratively extracts *every* well-formed JSON object from the model's output and deep-merges them.
- This allows the model to reason naturally without breaking the strict programmatic schema required by the application.

## The Dual Agent System
1. **Agent 1 (Discovery):** Responsible for evaluating initial input and defining the knowledge gap.
2. **Agent 2 (Intelligence):** Responsible for deep reading of evidence and exact specification extraction.

Splitting these tasks drastically improves accuracy compared to forcing a single LLM to execute the entire workflow simultaneously.
