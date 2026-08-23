# Troubleshooting Guide

This document provides exact solutions for verified issues you might encounter while running the UniHack application locally.

## 1. Application Hangs at Startup
**SYMPTOM:** The `npm run dev` script hangs at `[1/5] Checking Ollama...`
**WHY:** The startup script is struggling to spawn or communicate with the Ollama background process on Windows.
**CHECK:** Run `ollama ps` in a separate terminal.
**FIX:** Manually start Ollama in a separate terminal using `ollama serve`. Restart the `npm run dev` script.
**EXPECTED RESULT:** The startup script should instantly report `[OK] Ollama`.

## 2. Model Missing Error
**SYMPTOM:** The startup script fails with `[FAIL] qwen3.5:9b-q4_K_M is not installed.`
**WHY:** The required local model is not downloaded.
**CHECK:** Run `ollama list` and look for `qwen3.5:9b-q4_K_M`.
**FIX:** Run `ollama pull qwen3.5:9b-q4_K_M`. This is a ~6GB download.
**EXPECTED RESULT:** Startup script proceeds to step 3.

## 3. Wrong Frontend URL / Blank Page
**SYMPTOM:** You navigate to `http://localhost:5173` and see a login screen for FreeLLMAPI instead of UniHack.
**WHY:** Port collision. FreeLLMAPI claimed port 5173, so the Vite frontend silently moved to 5174, 5175, or higher.
**CHECK:** Look at the terminal output under `UNIHACK IS READY`.
**FIX:** Use the exact URL printed next to `UniHack Frontend:` (e.g., `http://localhost:5175`).
**EXPECTED RESULT:** The UniHack UI loads.

## 4. Pipeline Fails Immediately (Ollama 404)
**SYMPTOM:** You submit a product and it fails instantly. Backend logs show `404 Not Found` for `http://127.0.0.1:11434/api/chat`.
**WHY:** The backend is trying to request a model that Ollama doesn't have (historically caused by routing bugs sending Gemini requests to Ollama).
**CHECK:** Ensure you selected **LOCAL** mode in the UI.
**FIX:** The codebase has been fixed to prevent this via deterministic routing. If it recurs, ensure your local backend code is up to date and restart the backend.
**EXPECTED RESULT:** The pipeline progresses to the processing phase.

## 5. Pipeline Fails with 429 Too Many Requests
**SYMPTOM:** You submit a product and it fails with `FreeLLMAPI request failed: 429 Too Many Requests`.
**WHY:** The external proxy is rate-limiting your requests.
**CHECK:** Verify you are running in **LOCAL** mode. (Historically, a bug caused the UI to drop the `ai_mode` flag, defaulting to AUTO and hitting the proxy).
**FIX:** Ensure you explicitly select LOCAL in the UI.
**EXPECTED RESULT:** The pipeline routes strictly to Ollama.

## 6. Pipeline Takes 60 Minutes and Seems Stuck
**SYMPTOM:** The UI shows "Processing" for approximately 60 minutes without updating.
**WHY:** This is normal behavior for local inference. The 9B parameter model is generating thousands of tokens of reasoning across multiple agent stages.
**CHECK:** Run `ollama ps` in a separate terminal to verify the model is active (`100% CPU/GPU`).
**FIX:** Wait. Do not refresh the page.
**EXPECTED RESULT:** The UI will eventually update to VERIFIED once inference completes.

## 7. Stale Backend / Code Changes Not Reflecting
**SYMPTOM:** You made a code change, but the pipeline still exhibits an old bug.
**WHY:** The Uvicorn backend process might have been orphaned or not restarted correctly by the startup script.
**CHECK:** In Windows, run `Get-NetTCPConnection -LocalPort 8000` to find the stale PID.
**FIX:** Kill the stale python process manually (e.g., `taskkill /F /PID <PID>`).
**EXPECTED RESULT:** The next `npm run dev` starts a fresh backend process.
