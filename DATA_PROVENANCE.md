# Data Provenance

This document details the provenance and source of all data assets included in the repository.

## Raspberry Pi Pico Datasheet
- **Path**: `data_storage/validation/pico-datasheet.pdf`
- **Copyright Holder**: Raspberry Pi Ltd
- **Canonical Source URL**: https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf
- **Included Unchanged?**: Yes. The file is included exactly as distributed by the authoritative source.
- **Redistribution Permitted?**: Yes, the official datasheet is publicly released documentation by Raspberry Pi Ltd.
- **Purpose**: Used for testing the RAG implementation and vector retrieval with a realistic, high-quality technical document.

## Synthetic Test Fixtures
- **Paths**: `test_files/*`, `data_storage/validation/real_data_manifest.json`, `Frontend+Backend + Ai Engine/test_product.json`
- **Copyright Holder**: UniHack Team (TechnoTitans)
- **Canonical Source URL**: This repository.
- **Included Unchanged?**: Yes.
- **Redistribution Permitted?**: Yes, these files were created by the project team for testing purposes.
- **Purpose**: Provide deterministic, simple inputs to validate multimodal ingestion pipelines, CSV parsers, and API endpoint schemas.
