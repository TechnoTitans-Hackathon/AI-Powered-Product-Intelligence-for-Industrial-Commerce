# UniHack 2026: AI-Powered Product Intelligence Platform

## Overview
This platform automates the ingestion, analysis, and validation of industrial supplier documents and URLs. It solves the critical bottleneck of manually extracting structured intelligence (certifications, compliance standards, technical specs) from highly unstructured PDFs and web pages.

## Solution
We built a multi-agent AI engine using FastAPI and a local React/Vite frontend. The AI engine orchestrated via LangChain uses two local endpoints:
- A local Ollama instance (serving `qwen3.5:9b`).
- A `freellmapi` proxy endpoint (serving `gpt-oss-120b`).

## Quick Links
- [Architecture Details](ARCHITECTURE.md)
- [AI Models Strategy](AI_MODELS.md)
- [Datasets and Provenance](DATASETS_AND_DATA.md)
- [Judge Quickstart](JUDGE_QUICKSTART.md)

## Workspace Structure
- `Frontend+Backend + Ai Engine/`: The core UniHack application.
- `freellmapi/`: A third-party OpenAI-compatible proxy interface to local/remote models. Included under MIT License (see `THIRD_PARTY_LICENSES.md`).

## Documentation

To fully understand the architecture, data provenance, and limitations of this system, please review the following comprehensive documentation:

- **[Architecture & How It Works](./ARCHITECTURE.md) | [Simple Explanation](./HOW_IT_WORKS.md)**
- **[Dataset Catalog](./DATASET_CATALOG.md) | [Data Provenance](./DATA_PROVENANCE.md) | [Real vs Synthetic](./REAL_VS_SYNTHETIC.md)**
- **[AI Models](./AI_MODELS.md)**
- **[API & Authentication](./API_AND_AUTHENTICATION.md)**
- **[Environment Setup](./ENVIRONMENT_VARIABLES.md)**
- **[Judge Quickstart](./JUDGE_QUICKSTART.md)**
- **[Security Overview](./SECURITY.md)**
- **[Limitations](./LIMITATIONS.md)**
- **[License Info](./LICENSE_INFO.md) | [Third-Party Licenses](./THIRD_PARTY_LICENSES.md) | [Dataset Licenses](./DATASET_LICENSES.md) | [Model Licenses](./MODEL_LICENSES.md)**
- **[Authorship & Acknowledgements](./AUTHORSHIP.md)**

## Setup & Running
1. Read the [Environment Variables](ENVIRONMENT_VARIABLES.md) guide and copy `.env.example` to `.env`.
2. Follow the [Judge Quickstart](JUDGE_QUICKSTART.md) for step-by-step evaluation setup.

The entire application can be started from the root directory using a single command:
```bash
npm run dev
```
