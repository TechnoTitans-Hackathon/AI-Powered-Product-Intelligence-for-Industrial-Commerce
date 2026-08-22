# AI Intelligence Engine

The core AI orchestration, decision-making, and enrichment system for the UniHack project.

This standalone component represents the "Brain" of the platform. It is fully decoupled from the ingestion, UI, and database layers, allowing it to be rapidly developed and tested using internal mocks before final integration.

## Documentation

- **[Architecture](ARCHITECTURE.md)**: Describes the bounded adaptive feedback loop, decoupled agent-adapter design, multimodal contracts, and temporary knowledge constraints.
- **[Environment Setup](ENVIRONMENT.md)**: How to set up and run this codebase independently.
- **[Testing Guide](TESTING.md)**: Information about the test suite and evaluation frameworks used.

## Features

- **Bounded Adaptive Feedback Loop**: Automatically triggers targeted research when knowledge is insufficient, bounded to a maximum of 3 iterations.
- **Temporary Knowledge Storage**: In-memory storage mock enforcing 4GB limits, LRU eviction, duplicate detection, and 7-day retention.
- **Anti-Hallucination Constraints**: Strictly categorizes unproven fields as `MISSING` rather than inventing data. Tracks conflicting evidence as `PENDING_REVIEW`.
- **Multimodal Contract Integration**: Pydantic schema strictly defining input combinations (PDF, Video, Images, OCR, Text).
- **Commerce-Ready Adapter**: Maps multi-dimensional data arrays into a flat 252-column schema ready for product upload.
