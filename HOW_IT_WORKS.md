# How It Works

UniHack's AI-Powered Product Intelligence platform orchestrates multiple forms of media into a single, cohesive intelligence pipeline. Here is a simple explanation of what happens behind the scenes.

## What happens when a user uploads...
- **A PDF?**: The system extracts the raw text and chunks it. The text is passed through an Embedding Model to turn sentences into mathematical vectors, which are saved in a local FAISS database. This enables Retrieval-Augmented Generation (RAG) to instantly answer highly specific technical questions using the exact text from the document.
- **An Image?**: The image is passed through a Vision SDK or OCR (Optical Character Recognition) module. Text, labels, and schematic structures are extracted and passed to the AI engine to analyze product defects or metadata.
- **A Video?**: The backend securely invokes FFmpeg to sample individual frames from the video. These frames are then analyzed by a vision-capable LLM to understand real-world mechanical behavior or physical anomalies over time.

## The Dual-Agent Engine
The system employs multiple specialized agents:
- **Agent 1 (Extractor)**: Focuses entirely on pulling raw facts, specs, and constraints from the uploaded media.
- **Agent 2 (Analyzer)**: Takes the facts from Agent 1, combines them with RAG database lookups, and generates final, actionable business intelligence.

## Local vs. External AI
- **Why use Local AI (e.g., Qwen)?**: Industrial commerce often involves highly confidential trade secrets. Local execution ensures that proprietary schemas or defect images never leave the internal network.
- **Why use External AI (e.g., via FreeLLMAPI)?**: For generalized reasoning or when immense computing power is required, the system can transparently route requests to state-of-the-art cloud models.

## The Trace Console & Evidence
The AI Engine doesn't just guess—it provides **Evidence**. When an inference is made, the Trace Console explicitly logs exactly which document chunk, image frame, or database record influenced the AI's decision, making the entire pipeline verifiable and auditable.
