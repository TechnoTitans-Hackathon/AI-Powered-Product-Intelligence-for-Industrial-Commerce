# Real vs. Synthetic Assets

This document explicitly identifies what components in this repository reflect **REAL AI inference and production logic** versus **SYNTHETIC fixtures** used for validation or testing.

## REAL Production Components
- **AI Inference Pipeline**: The multimodal pipeline runs real generative inference and embedding operations using live models (e.g., local Qwen 3.5 or external providers via FreeLLMAPI).
- **RAG & Evidence Engine**: The vector search and trace capabilities are fully functional and operate on live, extracted data.
- **Provider Routing**: Real proxy routing connects the application to active upstream LLM endpoints.
- **Public Validation Data**: `pico-datasheet.pdf` is a real, real-world datasheet used to objectively validate embedding and retrieval accuracy.

## SYNTHETIC Test Components
The following are strictly used as test fixtures and do not represent hardcoded intelligence or mock behavior in the core engine:
- `test_files/*` (e.g., `catalog.csv`, `document.pdf`, `image.png`, `video.mp4`): Lightweight synthetic files used to verify that the file-upload and basic parsing logic (like FFmpeg extraction or OCR) execute without errors.
- `Frontend+Backend + Ai Engine/test_product.json`: A synthetic JSON payload used to validate API schema parsing.
- `real_data_manifest.json`: A static manifest describing the test fixtures.

## Zero Hardcoded Intelligence
The production codebase contains **zero** hardcoded responses, mock providers, or fake intelligence. The application dynamically processes input and relies on authentic AI inference models.
