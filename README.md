# UniHack 2026: AI-Powered Product Intelligence Platform

> **From messy industrial product information to evidence-aware, commerce-ready product intelligence.**

## 🏆 What We Built

Industrial commerce data is fragmented across supplier pages, PDFs, datasheets, descriptions, and inconsistent product identifiers. Our platform turns that unstructured input into a structured product intelligence record with **field-level evidence, confidence, validation, conflict detection, and a 252-column commerce output**.

This is not a simple `LLM -> JSON` extractor. The system separates discovery, evidence retrieval, decisioning, intelligence synthesis, normalization, validation, provenance, and commerce mapping.

## ⚡ Judge Quickstart

Start from the repository root:

```bash
npm run dev
```

Then follow **[JUDGE_QUICKSTART.md](./JUDGE_QUICKSTART.md)** for setup and **[DEMO_WALKTHROUGH.md](./DEMO_WALKTHROUGH.md)** for the exact judge journey.

### Recommended demo

Use a fresh industrial product. Our final successful validation run used:

```text
Schneider Electric
Altivar Process ATV630
ATV630U55N4
Motors & Drives
```

The run completed as `COMPLETED / FINISHED` and produced 23 populated attributes, 1 missing field, 0 detected source conflicts, and 3 evidence chunks.

## 🧠 How It Works

```text
                 PRODUCT INPUT
                       │
                       ▼
              ┌─────────────────┐
              │  Discovery      │  ← identity + missing attributes
              │     Agent       │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Evidence        │  ← local knowledge / documents
              │ Retrieval       │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Knowledge       │  ← is evidence sufficient?
              │ Decision        │
              └───────┬─────────┘
                      / \
             enough? /   \ missing?
                   ▼       ▼
                 continue  Research / Acquisition
                    \       /
                     ▼     ▼
              ┌─────────────────┐
              │ Intelligence    │  ← enrichment + synthesis
              │ Agent           │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ Normalize +     │
              │ Validate        │
              └────────┬────────┘
                       │
              ┌────────┴─────────┐
              ▼                  ▼
        Evidence /          Confidence /
        Provenance          Conflicts
              \                  /
               └────────┬────────┘
                        ▼
              ┌─────────────────┐
              │ Commerce        │
              │ 252-Col Output  │
              └─────────────────┘
```

### Why the architecture matters

- **LLMs discover and synthesize; deterministic code enforces contracts.**
- **Evidence is first-class data**, not an afterthought.
- **Missing information stays missing** instead of being silently invented.
- **Conflicts are surfaced** for review.
- **Provider/AI mode is explicit**, preventing a LOCAL request from silently becoming an external request.
- **Commerce mapping is separated from reasoning**, making the output predictable and machine-consumable.

## 🤖 AI Strategy

The AI engine supports explicit processing policies rather than one hardcoded provider path.

The demonstrated LOCAL pipeline uses:

```text
Agent 1 / Discovery      -> Ollama / qwen3.5:9b-q4_K_M
Agent 2 / Intelligence   -> Ollama / qwen3.5:9b-q4_K_M
Routing                  -> deterministic evidence/pipeline state where possible
```

Other configured modes/providers can be used according to the project's AI policy configuration.

## 🔬 What the Final Demo Produced

For Schneider Electric `ATV630U55N4`, the completed result exposed:

| Layer | Demonstrated output |
|---|---|
| Identity | Schneider Electric, ATV630U55N4, Altivar Process ATV630 |
| Technical specs | 5.5 kW (7.5 hp), 380–480 V AC, IP21 / UL Type 1 |
| Applications | Industrial and fluid-management |
| Features | Power measurement, process monitoring, asset monitoring, Stop & Go, motor control |
| Structured descriptions | Short, long, retail, marketing descriptions |
| Evidence | Field-level provenance snippets and evidence chunks |
| Commerce | Manufacturer/brand/part data, descriptions, features, applications, attribute label/value/UOM mappings |

## 🛡️ Evidence, Validation & Explainability

The UI does not only show a final value. Dynamic Specifications expose:

- normalized value
- unit
- field status such as `DIRECTLY_SUPPORTED` or `INFERRED`
- confidence
- provenance/evidence snippet

The Sources & Evidence view exposes grounding and document snippets so a judge can inspect why a value was accepted.

## 🧯 Engineering Journey: What Broke and How We Fixed It

We deliberately preserved the real debugging history because it demonstrates how the system was hardened rather than pretending the first implementation worked perfectly.

Major incidents included:

1. **Wrong frontend on an occupied port** → hardened startup detection.
2. **Ollama HTTP 404** → explicit Ollama provider/model routing.
3. **Stale Uvicorn process** → identify PID, terminate stale runtime, restart.
4. **Pydantic `required_attributes` type crash** → normalize LLM objects into the canonical `list[str]` contract.
5. **Empty Ollama response after HTTP 200** → increase inference headroom and harden output handling.
6. **`num_predict` truncating Qwen before JSON** → remove overly aggressive output cap.
7. **Multiple JSON blocks / array root** → robust JSON scanning and object merging.
8. **Expensive LLM routing call** → deterministic routing where evidence state is sufficient.
9. **LOCAL batch becoming AUTO** → propagate `ai_mode` from UI → API → job service → engine policy.
10. **FreeLLMAPI HTTP 429** → fixed the routing bug instead of masking it with retries.
11. **Ambiguous historical job monitoring** → inspect the exact current job ID / persisted job record.

Read the complete forensic history in **[REPAIR_HISTORY.md](./REPAIR_HISTORY.md)**.

## 📊 Final Validation Snapshot

The final fresh-product run completed successfully:

```text
Product:             Schneider Electric ATV630U55N4
Pipeline:             COMPLETED / FINISHED
Populated attributes: 23
Missing information:  1 field
Source conflicts:     0 detected
Evidence chunks:      3
Validation issues:    1 shown in UI
```

### Transparency matters

The successful demonstration still displayed a validation/conflict badge and a header-level manufacturer mismatch (`Unknown` in the header while the extracted manufacturer field was `Schneider Electric`). We intentionally document this limitation rather than hiding it. The system's goal is **evidence-aware intelligence with visible uncertainty**, not false certainty.

## 📁 Documentation Map

### Judge-facing
- **[Judge Quickstart](./JUDGE_QUICKSTART.md)** — setup and evaluation.
- **[Demo Walkthrough](./DEMO_WALKTHROUGH.md)** — step-by-step product demo.
- **[Repair History](./REPAIR_HISTORY.md)** — real failure → diagnosis → fix timeline.

### Architecture & AI
- **[Architecture Details](./ARCHITECTURE.md)**
- **[How It Works — Simple Explanation](./HOW_IT_WORKS.md)**
- **[AI Models Strategy](./AI_MODELS.md)**

### Data & provenance
- **[Dataset Catalog](./DATASET_CATALOG.md)**
- **[Datasets and Provenance](./DATASETS_AND_DATA.md)**
- **[Data Provenance](./DATA_PROVENANCE.md)**
- **[Real vs Synthetic](./REAL_VS_SYNTHETIC.md)**

### Operations & security
- **[Environment Variables](./ENVIRONMENT_VARIABLES.md)**
- **[API & Authentication](./API_AND_AUTHENTICATION.md)**
- **[Security Overview](./SECURITY.md)**
- **[Limitations](./LIMITATIONS.md)**

### Legal / attribution
- **[License Info](./LICENSE_INFO.md)**
- **[Third-Party Licenses](./THIRD_PARTY_LICENSES.md)**
- **[Dataset Licenses](./DATASET_LICENSES.md)**
- **[Model Licenses](./MODEL_LICENSES.md)**
- **[Authorship & Acknowledgements](./AUTHORSHIP.md)**

## 🧱 Repository Structure

```text
.
├── Frontend+Backend + Ai Engine/   # core application
├── freellmapi/                     # OpenAI-compatible proxy component
├── ARCHITECTURE.md
├── AI_MODELS.md
├── JUDGE_QUICKSTART.md
├── DEMO_WALKTHROUGH.md
├── REPAIR_HISTORY.md
└── ...
```

## 🚀 One Command to Run

```bash
npm run dev
```

See the judge guide for environment/model requirements before the first run.

## 🎯 Core Design Philosophy

> **Do not make AI output look trustworthy. Make the system show why it is trustworthy — and where it is not.**

That principle drives the evidence layer, field-level provenance, validation/conflict signals, explicit AI modes, deterministic contracts, and commerce-ready output.
