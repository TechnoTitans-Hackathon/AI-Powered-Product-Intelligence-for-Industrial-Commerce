# Final Judge Quickstart

Welcome! This guide assumes no prior context and will walk you through launching and observing the UniHack application on a Windows environment.

## A. Prerequisites
- **OS:** Windows 10/11
- **Node.js:** v18+ (with npm)
- **Python:** 3.10+ (with pip)
- **Ollama:** Installed and running locally.

## B. Repository Path Assumptions
This guide assumes you are executing commands from the root directory of the repository:
`D:\Hackathon`

## C. Node/npm Environment
Ensure all node modules are installed in the root directory and in `Frontend+Backend + Ai Engine/frontend`:
```cmd
npm install
cd "Frontend+Backend + Ai Engine/frontend"
npm install
cd ../..
```

## D. Python Environment
Ensure the Python virtual environment is set up and dependencies are installed in the `Frontend+Backend + Ai Engine` directory:
```cmd
cd "Frontend+Backend + Ai Engine"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

## E. Ollama Setup
UniHack relies heavily on local AI inference for privacy and cost control. You must have Ollama running.
```cmd
ollama serve
```

## F. Required Model
The system is explicitly tuned for the Qwen 3.5 9B model. You must pull it before starting:
```cmd
ollama pull qwen3.5:9b-q4_K_M
```

## G. Required Ports
Ensure the following local ports are free:
- **11434** (Ollama)
- **3001** (FreeLLMAPI fallback/proxy)
- **8000** (FastAPI Backend)
- **5175, 5176, 5177, or 5178** (Vite Frontend will dynamically claim one)

## H. Environment Setup
Create a `.env` file in the `Frontend+Backend + Ai Engine` directory if it does not exist, containing necessary configurations (see `ENVIRONMENT_VARIABLES.md` for details, though the system runs fully locally without external keys in LOCAL mode).

## I. First-Run Requirements
Ensure you have completed all prerequisites (Node, Python, Ollama, model pull).

## J. Startup Command
Start the entire stack using the unified NPM runner from the repository root:
```cmd
npm run dev
```

## K. Browser URL
**Crucial:** Do not assume the frontend is on port 5173. The startup script (`startup.js`) will verify the actual Vite frontend and print the exact URL to the terminal.
Look for this output in your terminal:
```text
==========================================
UNIHACK IS READY
==========================================
UniHack Frontend: http://localhost:5175
Backend:          http://127.0.0.1:8000
FreeLLMAPI API:   http://127.0.0.1:3001/v1
==========================================
```
Copy and paste the `UniHack Frontend` URL into your browser.

## L. First Demo Product
To test the pipeline, use this known, fresh product:
- **Brand:** Schneider Electric
- **Product Name/Family:** Altivar Process ATV630
- **Part Number:** ATV630U55N4

## M. What Judges Should Click
1. Open the Frontend URL.
2. Navigate to the **Upload/Process Product** section.
3. Enter the demo product details above.
4. Select the category **Motors & Drives**.
5. Select **LOCAL** mode (this guarantees it uses your local Ollama instance).
6. Click **Submit / Process**.

## N. What Judges Should Observe
You will see a loading/progress modal indicating the pipeline is running.
**Note:** Because local inference with a 9B parameter model requires deep reasoning, this process will take **approximately 60 minutes of wall-clock time** depending on your hardware. This is expected behavior.

## O. What Each Stage Means
- **Discovery:** The AI identifies what is already known and what specs are missing.
- **Evidence Retrieval:** The system fetches context/chunks to support the missing data.
- **Knowledge Decision:** The system decides if it has enough data or needs to halt/research.
- **Intelligence / Extraction:** The AI synthesizes the evidence and outputs the raw JSON specs.
- **Normalization & Validation:** The deterministic engine maps the JSON to the 252-column schema and checks it against the evidence.

## P. Expected Final Result
The UI should eventually display a success screen showing:
- Pipeline status: **VERIFIED**
- Populated attributes: **23** (approximate)
- Missing information: **1 field**
- Source conflicts: **0 detected**
- Evidence chunks: **3**

## Q. Troubleshooting
If the pipeline hangs or returns a 404, verify:
- Ollama is running (`ollama ps`).
- The Qwen model is successfully loaded.
- Check `TROUBLESHOOTING.md` for detailed fixes for known edge cases.

## R. Shutdown
When finished, press `Ctrl+C` in the terminal running `npm run dev`. The startup script will aggressively hunt down and kill all spawned processes (Ollama, Uvicorn, Vite) to leave your system clean.
