# UniHack Repair History & Engineering Journey

This document records the major runtime failures discovered during UniHack development, how each failure was isolated, and the architectural fix that resolved it. The goal is reproducibility and transparency for judges, reviewers, and future maintainers.

> **Important:** This is a real debugging history, not a fabricated success narrative. Resolved issues are documented as resolved; remaining limitations are explicitly called out.

## Final Verified Milestone

A fresh-product end-to-end run was completed successfully for:

- **Brand:** Schneider Electric
- **Product:** Altivar Process ATV630
- **Part Number:** ATV630U55N4
- **Category:** Motors & Drives
- **AI Mode:** AUTO
- **Pipeline status:** `COMPLETED` / `FINISHED`
- **Populated attributes:** 23
- **Missing information:** 1 field
- **Source conflicts:** 0 detected
- **Evidence chunks:** 3
- **Validation:** 1 validation issue remained visible in the UI

The successful run produced field-level evidence/provenance snippets, normalized technical values, feature/application extraction, and the 252-column commerce output.

## Incident 1 — Single-command startup initially launched the wrong frontend

### Symptom
`npm run dev` reported a frontend URL, but the browser opened the FreeLLMAPI dashboard instead of the UniHack React application.

### Root cause
Port `5173` was already occupied by the FreeLLMAPI frontend. The initial orchestration logic treated the port as sufficient evidence that the desired frontend was running.

### Fix
The startup orchestrator was hardened to identify the actual UniHack Vite frontend rather than trusting the port alone. It detects the bound frontend URL and avoids mistaking the FreeLLMAPI dashboard for UniHack.

### Result
The one-command launcher can now coexist with already-running services without attaching the judge to the wrong UI.

## Incident 2 — Ollama returned HTTP 404 for `/api/chat`

### Symptom
UniHack returned:

```text
OllamaProvider analysis failed: Client error '404 Not Found'
for url 'http://127.0.0.1:11434/api/chat'
```

### Root cause
Ollama itself was healthy and the expected model existed. The backend model-selection fallback did not explicitly handle the `ollama` provider, so it could resolve a Gemini model name for an Ollama request.

### Fix
The provider policy now maps the Ollama path explicitly to:

```text
qwen3.5:9b-q4_K_M
```

The runtime backend was also restarted so the process actually loaded the corrected source code.

### Verification
A direct Ollama request returned HTTP 200, and UniHack diagnostics showed the same Qwen model reaching `/api/chat`.

## Incident 3 — The code was fixed but the running backend was stale

### Symptom
The model-routing source code was correct on disk, but runtime logs still showed the old behavior.

### Root cause
The startup orchestrator correctly reused the already-running backend on port 8000. Uvicorn had been started without hot reload, so the old Python process kept executing the previous in-memory code.

### Fix
The exact backend PID was identified and terminated, then a fresh Uvicorn process was launched from the project virtual environment.

### Lesson
A source-code fix is not a runtime fix until the process containing the old code has been restarted.

## Incident 4 — `RetrievalRequest` rejected `required_attributes`

### Symptom
Pydantic reported errors such as:

```text
required_attributes.0
Input should be a valid string
input_type=dict
```

### Root cause
The Discovery LLM sometimes returned rich objects such as:

```json
{"attribute":"power_rating","reason":"load protection sizing"}
```

while downstream retrieval correctly required `list[str]`.

### Fix
The Discovery agent became a strict normalization boundary. Dictionary entries are converted to their attribute-name strings before entering the canonical retrieval contract. Supporting reason metadata remains in the appropriate evidence-requirement structure.

### Result
The Pydantic contract stayed strict; the fix was applied at the producer boundary instead of weakening downstream validation.

## Incident 5 — Qwen completed HTTP 200 but returned an empty final response

### Symptom
Ollama returned HTTP 200 but UniHack saw:

```text
No JSON object or array found in Ollama response.
Original: ''
```

### Root cause
The local Qwen build spends substantial output budget in its reasoning/thinking channel. With a small context/output budget, generation could terminate while still reasoning, leaving the final `response` field empty.

### Fix
The local inference configuration was hardened to give the model enough room to complete. Context and timeout settings were made configurable, and the provider stopped retrying deterministic failures such as malformed output, 404, and non-transient authentication errors.

## Incident 6 — Limiting `num_predict` too aggressively truncated valid JSON

### Symptom
A `num_predict` cap such as `512` or `1500` cut the model off before it emitted the final JSON document, causing JSON parsing failures.

### Root cause
Qwen spent part of the generation budget on its internal reasoning text before producing the structured response.

### Fix
The production path no longer relies on an overly small generation cap. The parser is designed to tolerate the model's verbose response format instead of assuming the model will obey a tiny output budget.

### Result
The Discovery stage successfully produced usable JSON in the final successful pipeline run.

## Incident 7 — Qwen returned multiple JSON blocks / arrays

### Symptom
The parser sometimes received a response shaped like multiple separate code blocks, for example a product-identity object followed by an actions array. The previous parser could select the final array and downstream code would then fail with:

```text
'list' object has no attribute 'get'
```

### Root cause
The model did not consistently return one clean top-level object even when instructed to do so.

### Fix
`_parse_json_response` was reworked around Python's JSON decoder to scan the response for valid JSON values, ignore surrounding reasoning text, select compatible object roots, and merge relevant object fragments before passing the result to the schema layer.

### Result
The Discovery stage passed with the new parser and the pipeline moved to downstream intelligence processing.

## Incident 8 — The router added an unnecessary expensive Qwen inference

### Symptom
The local pipeline could spend another several minutes asking Qwen whether Agent 2 was required even when existing evidence state already provided enough information to make that routing decision.

### Root cause
Agent-2 routing was implemented as another structured LLM call.

### Fix
Routing was moved to deterministic pipeline state where possible. The existing evidence sufficiency / conflict signals are used to decide whether Agent 2 is actually required, avoiding an unnecessary local-LLM round trip.

### Result
The final E2E test moved from Discovery directly into the Intelligence Agent without spending another full Qwen inference on routing.

## Incident 9 — Batch Processing ignored the user's AI mode

### Symptom
A user-selected LOCAL batch run reached FreeLLMAPI and failed with HTTP 429.

### Root cause
The Batch Processing endpoint created jobs without passing the `ai_mode` supplied by the UI. The job-service default was AUTO, so the user intent was silently lost.

### Fix
The mode now flows end-to-end:

```text
Batch UI selector
    -> frontend API client
        -> FastAPI /batch endpoint
            -> job_service.create_job(..., ai_mode=...)
                -> EngineService policy
```

The Batch Processing UI also exposes the AI mode explicitly.

### Result
LOCAL batch jobs remain LOCAL and do not silently fall through to external providers.

## Incident 10 — Historical jobs confused runtime monitoring

### Symptom
`/api/v1/jobs` returned many historical records, making it easy to believe an old failed/processing job was the current GUI run.

### Root cause
The monitoring approach relied on list ordering rather than the exact current job ID.

### Fix / Operating procedure
For final validation, record the job ID created by the current GUI request and inspect that job directly. The persisted SQLite `processing_jobs` record was used as the authoritative debugging source when the listing endpoint was ambiguous.

## Incident 11 — FreeLLMAPI 429 was initially misattributed to the core LOCAL pipeline

### Symptom
A 429 from `http://localhost:3001/v1/chat/completions` looked like a provider reliability problem.

### Root cause
The 429 belonged to the Batch Processing path that had accidentally downgraded the requested LOCAL mode to AUTO.

### Fix
The API-level `ai_mode` propagation bug was fixed first. This removed the unintended FreeLLMAPI call path for LOCAL batch processing instead of hiding the 429 with retries or fake fallbacks.

## Final Architecture After Repair

```text
Judge / User
    |
    v
React / Vite Frontend
    |
    v
FastAPI Backend
    |
    v
Engine Service / AI Policy
    |
    +--> Discovery Agent --------+
    |                            |
    +--> Evidence Retrieval      |
    |                            v
    +--> Deterministic Routing -> Intelligence Agent
    |                            |
    +--> Normalization ---------+
    +--> Validation
    +--> Confidence
    +--> Commerce 252-Col Output
    |
    +--> Evidence / Provenance

LOCAL mode:
    Agent 1 = Ollama/Qwen
    Agent 2 = Ollama/Qwen
    Router = local/deterministic where possible
    External acquisition = disabled

AUTO/FAST/DEEP:
    Provider policy is selected explicitly by mode/configuration.
```

## Final Operating Principles

1. Fix provider routing at the boundary instead of hiding provider errors.
2. Keep Pydantic contracts strict and normalize LLM outputs at producer boundaries.
3. Treat model output as untrusted structured data and validate it.
4. Never use a mock, fabricated result, or hardcoded product data to claim success.
5. Restart stale runtimes after source changes.
6. Prefer deterministic operations for routing, normalization, validation, and confidence.
7. Preserve evidence and provenance for extracted values.
8. Monitor the exact current job, not the historical job list.

## Known Remaining Limitation in the Demonstrated Run

The successful Schneider Electric demonstration showed **23 populated fields**, **1 missing field**, and **0 detected source conflicts**, but the UI still displayed **one validation issue** and a `CONFLICT` confidence badge. The manufacturer header also displayed `Unknown` while the extracted manufacturer field was `Schneider Electric`. These are visible limitations of the demonstrated result and should be described honestly rather than hidden.
