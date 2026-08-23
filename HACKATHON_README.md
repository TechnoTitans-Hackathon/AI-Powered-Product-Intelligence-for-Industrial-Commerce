# UniHack: Autonomous Product Intelligence

**Problem:** Incomplete, inaccurate, and unstructured product data plagues industrial commerce, leading to supply chain friction, procurement errors, and wasted engineering hours.

**Solution:** An autonomous, AI-driven pipeline that takes bare minimum product identifiers (like brand and part number), discovers missing specifications, retrieves supporting evidence, and normalizes the data into a strict 252-column commerce-ready schema—all while assigning explicit confidence scores based on verifiable evidence.

## What UniHack Actually Does
UniHack is an end-to-end evidence-based data engine. It does not just ask an LLM to hallucinate product details. Instead, it:
1. Accepts partial product inputs.
2. Uses local AI (Ollama + Qwen3.5) to identify what is known and what is missing.
3. Retrieves real-world evidence.
4. Determines if it has enough knowledge to proceed.
5. Normalizes the extracted facts against a rigorous commerce schema.
6. Validates every claim against the retrieved evidence, flagging conflicts.
7. Outputs a highly structured, fully explained product record with provenance.

## Key Differentiators
- **Evidence-Based Extraction:** If we can't find it, we don't invent it.
- **Deterministic Validation:** AI generates the initial extraction, but deterministic rule-engines perform the validation and conflict detection.
- **Strict Commerce Schema:** Data is mapped into 252 normalized industrial commerce attributes, not arbitrary JSON.
- **Honest Confidence Scoring:** Missing fields are left `null` with low confidence rather than being populated with hallucinations.
- **Local-First AI architecture:** Runs entirely on local Ollama models for privacy and cost-control, with the ability to scale to external APIs for deep research.

## Architecture
UniHack orchestrates a multi-agent AI pipeline combined with deterministic rule engines.
**User → React/Vite Frontend → FastAPI Backend → Job Service → AI Processing Policy → AI Engine Pipeline → (Discovery → Evidence Retrieval → Knowledge Decision → Intelligence Synthesis) → Normalization → Validation → Confidence Scoring → Commerce Schema output.**

## AI Strategy
UniHack utilizes a multi-mode AI architecture:
- **LOCAL Mode:** Everything runs via Ollama (using `qwen3.5:9b-q4_K_M`) to guarantee zero data leakage.
- **AUTO / FAST / DEEP Modes:** Future-proofed routing policies designed to escalate complex tasks to external frontier models (like GPT or Claude) only when required.

## Evidence Strategy & Provenance
UniHack relies on "chunks" of evidence retrieved during its discovery phase. The Intelligence Agent is strictly prompted to derive its answers only from these retrieved chunks. Every claim is mapped back to its source, providing complete provenance and accountability for the data.

## Validation & Confidence Scoring
Extracted values are checked against the evidence. The pipeline explicitly supports detecting:
- **DIRECTLY_SUPPORTED:** The fact is directly stated in the evidence.
- **INFERRED:** The fact is heavily implied but not explicitly stated.
- **MISSING:** The evidence does not contain the fact.
- **CONFLICT:** The extracted fact contradicts the evidence.
This allows UniHack to assign a confidence score to every data point.

## Commerce-Ready Output
The final product is a 252-column dataset designed for industrial ERPs and PIM systems. It groups data into logical families (Identity, Features, Attributes, UOM, Compliance, etc.). Nulls are preserved where data is genuinely missing, ensuring downstream data integrity.

## Fresh-Product Demonstrated Result
We performed a real-world, cold-start run on an industrial component:
- **Product:** Schneider Electric Altivar Process ATV630 (ATV630U55N4)
- **Observed Result:** Pipeline status VERIFIED. 23 attributes populated, 1 field missing, 0 source conflicts, powered by 3 evidence chunks.

## Performance Reality & Limitations
- **Latency:** Because UniHack prioritizes local execution (Ollama) and multi-step reasoning, processing a single product takes approximately 60 minutes of wall-clock time. This is a batch-processing architecture, not a real-time autocomplete engine.
- **Incomplete Evidence:** If the target product lacks public documentation, UniHack will honestly return empty fields rather than fabricating data.

## Technology Stack
- **Frontend:** React + Vite + TailwindCSS
- **Backend:** Python + FastAPI + Uvicorn
- **AI Engine:** LangChain/Pydantic-based orchestrator
- **Local Models:** Ollama (`qwen3.5:9b-q4_K_M`)
- **Proxy/Fallback:** FreeLLMAPI

## Repository Map
- [Judge Quickstart](JUDGE_QUICKSTART_FINAL.md) - Start here!
- [How It Works](HOW_IT_WORKS.md) - Plain English explanation
- [Architecture Deep Dive](ARCHITECTURE_DEEP_DIVE.md) - System architecture
- [Live Demo Walkthrough](DEMO_WALKTHROUGH.md) - Script for demoing
- [Engineering Journey](ENGINEERING_JOURNEY.md) - Timeline of development and bug fixes
- [Full Documentation Index](DOCUMENTATION_INDEX.md) - Links to all docs
