# AI Intelligence Engine - Architecture

This document describes the standalone AI Engine architecture developed for the UniHack project. It is designed to be fully decoupled from the yet-to-be-built ingestion backends, database layers, and frontends.

## Core Architectural Principles

1. **Separation of Concerns via Interfaces:** 
   The AI Brain operates purely on abstraction interfaces (`AIProviderInterface`, `RetrieverInterface`, `ResearchInterface`). It knows nothing about the underlying database technology or web scraper.
2. **Adapter-Agent Pattern:** 
   Agents orchestrate logic, while adapters (like the `CommerceOutputAdapter`) handle data formatting. 
3. **Pydantic-Driven Contracts:** 
   All cross-boundary data flows are strictly typed via Pydantic schemas. 

## The Pipeline (Bounded Adaptive Feedback Loop)

The `ProductIntelligencePipeline` is the primary orchestrator. It follows a 10-step adaptive flow:

1. **Normalization:** Raw `ProductInput` is normalized into a standard `NormalizedInput` multimodal struct.
2. **Discovery (Agent 1):** Determines what the product is (identity resolution) and what information is missing.
3. **Initial Retrieval:** Fetches available internal knowledge via the `RetrieverInterface`.
4. **Knowledge Decision (Adaptive Engine):** Evaluates if the evidence is sufficient, conflicting, or sparse.
5. **Targeted Research (Loop):** If evidence is insufficient, it triggers targeted web research up to a maximum of 3 iterations (Bounded Feedback Loop), deduplicating and appending new knowledge dynamically.
6. **Intelligence Enrichment (Agent 2):** Best-effort extraction based on the gathered evidence.
7. **Normalization Engine:** Unifies values and units (e.g., mapping `1/2 in` to `0.5 in`).
8. **Validation Engine:** Checks for missing critical data and internal logic consistency.
9. **Confidence Engine:** Calculates signal-based confidence scores, penalizing conflicting data or weak sources.
10. **Commerce Output Adapter:** Maps the high-dimensional intelligence struct into the exact flat 252-column schema required by the downstream commerce system.

## Multimodal Contract

The engine accepts data through a strictly defined `NormalizedInput` multimodal contract, accommodating:
- **Text:** Plain text, PDF content, Docs.
- **Visual:** Images, Diagrams, OCR results.
- **Structured:** Tables, CSVs, Excel data.
- **Video:** Keyframes, Transcripts, Timestamps.

## Temporary Knowledge Lifecycle

The knowledge system (`TemporaryKnowledgeStore`) uses an in-memory mock designed to enforce strict limits:
- **4GB Limit:** Enforced via naive estimation and LRU eviction.
- **Retention:** 7-day TTL since `last_used_at`.
- **Deduplication:** Hash and URL-based deduplication to prevent redundant cache pollution.

## Anti-Hallucination & Best-Effort Safety

The system implements strict safety constraints to prevent hallucinations:
- **Never Guess:** If evidence is missing, the system outputs `FieldStatus.MISSING`.
- **Conflict Tracking:** If two sources conflict (e.g., Datasheet vs Website), a `Conflict` object is generated and the status becomes `PENDING_REVIEW`.
- **Inferred Warnings:** If the AI deduces information without direct textual support, the status becomes `FieldStatus.INFERRED` and confidence is penalized.
