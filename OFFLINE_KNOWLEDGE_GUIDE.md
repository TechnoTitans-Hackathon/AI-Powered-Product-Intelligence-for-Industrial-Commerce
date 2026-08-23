# OFFLINE KNOWLEDGE GUIDE

## Directory Structure
The offline knowledge corpus resides in the following runtime directory:
`D:\Hackathon\Frontend+Backend + Ai Engine\data_storage\permanent_knowledge`

All downloaded `.csv` and `.ttl` files, as well as metadata logs, exist in this single centralized location.

## Retrieval Engine
- **Class:** `backend.retrieval.vector_store.InMemoryVectorStore`
- **Orchestration:** `backend.retrieval.retrieval_service.RetrievalService`

When the backend starts, the retrieval service indexes the parsed baseline chunks from the dataset registry. 

## Dataset Manifests
The `permanent_knowledge_manifest.json` file in the knowledge directory acts as the master record. It tracks:
- Dataset ID and Source
- Cryptographic checksums (SHA-256)
- Licenses
- Indexed state

## Adding Data (Not Recommended for Judges)
The offline corpus is considered sealed for the UniHack submission. However, if new data must be acquired, it should be done using the `tools/permanent_knowledge_acquisition.py` script to ensure strict licensing, anti-fabrication, and size limit checks (2 GB limit).
