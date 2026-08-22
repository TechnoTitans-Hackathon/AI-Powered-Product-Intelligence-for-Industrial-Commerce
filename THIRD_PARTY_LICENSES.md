# Third Party Licenses

## FreeLLMAPI
The workspace includes the `freellmapi` source code, which serves as a critical local proxy endpoint for the AI engine.
- **License**: MIT License
- **Copyright**: 2026 Tashfeen Ahmed
- **Usage**: Included directly in this repository for local proxy orchestration.

## 2. Python Backend Dependencies
The backend relies on numerous open-source Python packages (verified via `pip freeze`), primarily distributed under permissible licenses (MIT, Apache 2.0, BSD). Key libraries include:
- **FastAPI / Starlette / Pydantic**: MIT License
- **Uvicorn**: BSD License
- **PyMuPDF**: AGPL (or commercial). *Note: Ensure AGPL compliance if deploying this specific configuration in a proprietary commercial environment.*
- **OpenCV-Python**: Apache 2.0 License
- **SentenceTransformers (via torch/transformers)**: Apache 2.0 / PyTorch License
- **FAISS / numpy / pandas**: MIT / BSD License
- **FFmpeg bindings**: Varies (LGPL/GPL based on the underlying compiled binary)

## 3. Node.js Frontend Dependencies
The React/Vite frontend relies on standard NPM packages, generally MIT licensed. Dependency lockfiles are included, but raw binaries/caches are explicitly excluded.
