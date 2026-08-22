# AI Intelligence Engine - Testing Guide

## Test Suite Overview

The `ai_engine/tests/test_engine.py` suite validates the end-to-end functionality of the standalone AI Engine, including the mocked boundaries where the ingestion, database, and backend systems will eventually live.

### Test Categories

1. **Schema Tests:** Validates Pydantic serialization, defaults, and evidence metric calculations.
2. **Provider Tests:** Ensures the `AIProviderInterface`, `RetrieverInterface`, and `ResearchInterface` return the correct types and data shapes.
3. **Agent Tests:** Checks `DiscoveryAgent` and `IntelligenceAgent` mapping and parsing behavior.
4. **Knowledge Decision Engine Tests:** Validates deterministic sufficiency logic (SUFFICIENT, RESEARCH_REQUIRED, INSUFFICIENT, IDENTITY_UNCERTAIN).
5. **Storage Tests:** Validates the `TemporaryKnowledgeStore` enforces 4GB limits, LRU eviction, duplicate detection, and 7-day retention.
6. **Anti-Hallucination Tests:** Ensures that unsupported specs remain `MISSING` and weak sources appropriately lower confidence.
7. **Pipeline Tests:** Validates the adaptive bounded feedback loop (up to 3 iterations) and the full 10-step orchestration logic.
8. **Fixture Scenarios:** Evaluates system resilience against sparse, missing, conflicting, and unknown product inputs using Multimodal Fixtures.

## Running Tests

Ensure you have `pytest` installed.

To run all tests with verbosity:
```bash
python -m pytest tests/test_engine.py -v
```

To run a specific test category (e.g. AntiHallucination):
```bash
python -m pytest tests/test_engine.py -v -k "TestAntiHallucination"
```

## Adding New Tests

When implementing concrete integrations for `AIProviderInterface` or `RetrieverInterface`:
1. Do **not** remove the `MockProvider` or `MockRetriever` tests, as they serve as baseline behavioral constraints.
2. Add a new test file (e.g. `test_gemini_provider.py`) implementing real API calls decorated with `@pytest.mark.integration`.
