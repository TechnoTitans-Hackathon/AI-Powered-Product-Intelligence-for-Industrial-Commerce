# Datasets and Data Provenance

## Real vs. Synthetic Data
This project was developed with a mix of synthetic data (for unit testing schema validation) and real-world datasets (for validating extraction pipelines).

### Validation Assets included in Source Control
- **pico-datasheet.pdf** (18MB)
  - **Source**: Raspberry Pi documentation.
  - **URL**: Publicly available via raspberrypi.com
  - **Purpose**: Used as a complex, multi-page technical specification document to validate zero-shot product parameter extraction.
  - **License/Distribution**: Assumed freely redistributable for educational/evaluation purposes.

### Excluded Production Data
To maintain repository health, the following are strictly excluded via `.gitignore`:
- `*.db` / SQLite databases containing generated output.
- `data_storage/vector_store/` containing local embeddings.
- `data_storage/temp_cache/` containing downloaded user PDFs.

These will automatically be generated in your local environment upon running the application.
