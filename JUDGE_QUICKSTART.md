# Judge Quickstart

Follow these steps to fully evaluate the UniHack Product Intelligence Platform locally.

## STEP 1: Initial Setup (Only first time)
1. Navigate to the root directory `D:\Hackathon\`.
2. Read the [Environment Variables](ENVIRONMENT_VARIABLES.md) guide and configure your `.env` if necessary.

*(If a separate setup script exists, you can run `npm run setup` here. Ensure `qwen3.5:9b-q4_K_M` model is pulled in Ollama).*

## STEP 2: Start the Application
Run the following single command from the root directory (`D:\Hackathon\`):

```bash
npm run dev
```

The orchestration script will automatically:
- Detect and reuse or start Ollama and verify the model.
- Detect and reuse or start the FreeLLMAPI proxy.
- Start the FastAPI backend.
- Start the Vite frontend.

## STEP 3: Evaluation
Open the frontend URL printed in the terminal by the orchestration script (e.g., `http://localhost:5173`).

You can now upload a sample PDF (such as the Pico Datasheet found in `Frontend+Backend + Ai Engine/data_storage/validation/`) or enter a supplier URL in the frontend to witness the AI Agent dynamically structuring the parameters.
