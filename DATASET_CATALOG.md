# Dataset Catalog

This document lists all datasets and static data assets included in the UniHack repository.

| Asset | Type | Real/Synthetic | Runtime/Validation | Size | Purpose |
| ----- | ---- | -------------- | ------------------ | ---- | ------- |
| `data_storage/validation/pico-datasheet.pdf` | PDF Document | Real | Validation | 17.3 MB | Official Raspberry Pi Pico datasheet used to validate RAG extraction and embedding accuracy. |
| `data_storage/validation/real_data_manifest.json` | JSON Manifest | Synthetic | Validation | < 1 KB | Describes the validation assets. |
| `test_files/catalog.csv` | CSV | Synthetic | Test Fixture | < 1 KB | Synthetic catalog for testing CSV ingestion pipelines. |
| `test_files/document.pdf` | PDF | Synthetic | Test Fixture | < 1 KB | Synthetic PDF for testing the ingestion pipeline. |
| `test_files/image.png` | Image | Synthetic | Test Fixture | < 1 MB | Synthetic image for testing multimodal vision ingestion. |
| `test_files/video.mp4` | Video | Synthetic | Test Fixture | < 1 MB | Synthetic video for testing video frame extraction and STT. |
| `Frontend+Backend + Ai Engine/test_product.json` | JSON | Synthetic | Test Fixture | < 1 KB | Synthetic product payload for testing the backend endpoints. |

## Excluded Assets
- SQLite Databases (`*.db`, `*.sqlite`, `*.sqlite3`) are explicitly excluded to prevent leaking generated runtime state or private information.
- Vector stores, embedding caches, and FAISS indices are excluded.

*Note: All data here is static and checked into version control.*
