# Judge Quickstart

This is the shortest reliable path for evaluating the UniHack Product Intelligence Platform locally.

## STEP 1 — Initial setup

1. Clone/download the repository.
2. Navigate to the repository root.
3. Read `ENVIRONMENT_VARIABLES.md` before changing configuration.
4. Ensure Ollama is installed and the configured local model is available:

```bash
ollama list
```

Expected model for the demonstrated LOCAL pipeline:

```text
qwen3.5:9b-q4_K_M
```

If the model is not present, pull the model configured by your team before starting the demo.

## STEP 2 — Start everything

From the repository root:

```bash
npm run dev
```

The orchestration script starts or reuses the required services and prints their status/URLs.

The important services are:

```text
Frontend   -> Vite / React
Backend    -> FastAPI / Uvicorn :8000
Ollama     -> local inference :11434
```

If another service already occupies a port, verify the URL printed by the UniHack launcher rather than assuming the occupied port belongs to UniHack.

## STEP 3 — Open the UniHack UI

Open the **UniHack frontend URL printed by the startup script**.

Do not confuse it with the optional FreeLLMAPI dashboard. FreeLLMAPI may exist as a separate service, but a LOCAL evaluation should use the UniHack frontend and the LOCAL AI policy.

## STEP 4 — Run a fresh product

Use the product ingestion/upload flow and provide a real industrial product.

A successful final validation run used:

```text
Brand:       Schneider Electric
Product:     Altivar Process ATV630
Part Number: ATV630U55N4
Category:    Motors & Drives
Industry:    Industrial
```

For a stronger evaluation, judges are encouraged to try a different product/manufacturer as well.

## STEP 5 — Choose AI mode

When the UI exposes the AI mode selector, choose:

```text
LOCAL
```

The selected mode is intentionally propagated through:

```text
UI -> API client -> FastAPI batch/job endpoint -> job service -> EngineService -> provider policy
```

This prevents a LOCAL request from silently becoming AUTO and accidentally using an external provider.

## STEP 6 — Start processing

Start the AI pipeline and allow the job to finish.

Local Qwen inference can take several minutes on consumer hardware. Do not refresh or terminate the backend while the current job is actively processing.

The conceptual stages are:

1. Reading Input & Multimodal Ingestion
2. Product Identity Discovery
3. Evidence Retrieval
4. Knowledge Decision Engine
5. Targeted Research & Acquisition (when permitted/required)
6. Intelligence / Enrichment
7. Normalization
8. Validation / Confidence / Conflict Detection
9. Commerce 252-Column Mapping
10. Field-Level Provenance

## STEP 7 — Inspect the result

### A. Overview & Metrics

Verify that the product identity is populated and inspect:

- populated attributes
- missing information
- source conflicts
- validation state
- overall pipeline status

### B. Dynamic Specifications

This is the main technical proof. Inspect field-level:

- normalized value
- unit
- grounding status
- confidence
- provenance snippet

### C. Features & Applications

Inspect semantic product features, applications, and industrial context.

### D. Descriptions & Taxonomy

Inspect generated structured short/long/retail/marketing descriptions and taxonomy information.

### E. Sources & Evidence

Inspect evidence chunks and field-level grounding. This demonstrates that the system is designed to explain where extracted values came from.

### F. Commerce 252-Col Schema

Inspect the final commerce mapping. The demonstrated result populated fields such as manufacturer part number, brand, manufacturer, product descriptions, features, applications, and attribute label/value/UOM entries.

## STEP 8 — What a judge should look for

The key evaluation question is not merely:

> "Did an LLM produce a product description?"

Instead, look for the complete chain:

```text
Unstructured product information
          ↓
Identity discovery
          ↓
What is known / what is missing?
          ↓
Evidence retrieval
          ↓
Evidence sufficiency decision
          ↓
Targeted acquisition when allowed
          ↓
Multi-agent intelligence
          ↓
Normalization + validation
          ↓
Confidence + conflict signals
          ↓
Field-level provenance
          ↓
Commerce-ready 252-column record
```

## STEP 9 — Verify the final job if needed

The backend persists processing jobs in the project database. During development/debugging, the exact current job ID was used to distinguish a live run from historical failures.

A completed job should ultimately show the equivalent of:

```text
STATUS: COMPLETED
STEP:   FINISHED
ERROR:  None
```

## STEP 10 — Optional stress test

For deeper evaluation, try:

- another manufacturer
- another industrial category
- incomplete product information
- conflicting specifications

The expected behavior is to expose missing/uncertain/conflicting information rather than silently presenting every generated value as verified fact.

## Final demonstrated result

The final fresh-product run completed successfully for Schneider Electric ATV630U55N4:

```text
Pipeline:             COMPLETED / FINISHED
Populated attributes: 23
Missing information:  1 field
Source conflicts:     0 detected
Evidence chunks:     3
Validation issues:    1 shown in UI
```

The demonstration displayed technical values including 5.5 kW (7.5 hp), 380–480 V AC, IP21 / UL Type 1, industrial/fluid-management applications, and multiple extracted features with provenance snippets.

### Transparency note

The demonstrated result still showed one validation/conflict issue and a header-level manufacturer mismatch (`Unknown` in the header while the extracted manufacturer field was `Schneider Electric`). This is a known limitation of that result and is intentionally documented. Judges should treat the visible validation/provenance signals as part of the system's behavior, not as hidden implementation details.

## Full documentation

- [Demo Walkthrough](DEMO_WALKTHROUGH.md)
- [Repair History](REPAIR_HISTORY.md)
- [Architecture](ARCHITECTURE.md)
- [AI Models](AI_MODELS.md)
- [Limitations](LIMITATIONS.md)
