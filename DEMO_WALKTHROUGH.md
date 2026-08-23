# Judge Demo Walkthrough

This guide is the shortest path for a judge to understand and demonstrate the platform from input to commerce-ready output.

## 1. Start the platform

From the repository root:

```bash
npm run dev
```

The orchestrator starts/reuses the required services and prints the application URLs.

For a local AI demonstration, ensure Ollama has the configured model:

```bash
ollama list
```

Expected model:

```text
qwen3.5:9b-q4_K_M
```

## 2. Open the UniHack frontend

Open the UniHack frontend URL printed by the startup script. Do not use the FreeLLMAPI dashboard if it is running on another port.

## 3. Create or select a product

Use the product ingestion/upload flow. A useful demonstration is an industrial product with a recognizable manufacturer and part number.

Example demonstrated successfully during final validation:

```text
Brand: Schneider Electric
Product: Altivar Process ATV630
Part Number: ATV630U55N4
Category: Motors & Drives
Industry: Industrial
```

The point of the demo is not to hardcode this product; it is to show that a fresh product can traverse the pipeline.

## 4. Select processing mode

For an isolated local demonstration, select `LOCAL` where the UI provides the AI mode selector.

This is important because AI mode is intentionally propagated from the UI through the API and job service. A LOCAL request must not silently become AUTO.

## 5. Start processing

Click the processing action. The pipeline progresses through the following conceptual stages:

1. **Reading Input & Multimodal Ingestion** — parse raw text, URLs, documents, and structured input.
2. **Product Identity Discovery** — identify product name, brand, part number, category, and required attributes.
3. **Evidence Retrieval** — retrieve relevant local knowledge/evidence.
4. **Knowledge Decision Engine** — determine whether evidence is sufficient.
5. **Targeted Research & Acquisition** — acquire missing information when the selected mode permits it.
6. **Intelligence / Synthesis** — normalize and enrich the product record.
7. **Validation & Confidence** — identify unsupported values, conflicts, missing fields, and confidence.
8. **Commerce Mapping** — map the canonical product intelligence into the 252-column commerce schema.
9. **Provenance** — retain field-level evidence snippets and grounding status.

## 6. Watch the result

The result page exposes several judge-friendly views.

### Overview & Metrics

Look for:

- Product identity
- Populated attribute count
- Missing information
- Source conflicts
- Pipeline verification state

### Dynamic Specifications

This is the strongest technical proof. Each extracted field can show:

- normalized value
- unit
- field status
- confidence
- source/provenance snippet

### Features & Applications

Shows semantic extraction beyond simple key/value parsing, including product features, applications, and industry context.

### Descriptions & Taxonomy

Shows generated structured commerce descriptions such as short, long, retail, and marketing descriptions.

### Sources & Evidence

Shows field-level grounding, evidence chunks, and document snippets. This is where judges can inspect why a value was accepted.

### Commerce 252-Col Schema

Shows how the normalized intelligence is mapped into an ecommerce catalog format. Populated columns include product description, manufacturer part number, brand, manufacturer, descriptions, features, applications, and attribute label/value/UOM fields when available.

## 7. What to ask the system

A judge can evaluate the platform with a new industrial product rather than only the demonstrated example. Good tests include:

- a different manufacturer
- a different category such as bearings, hydraulics, electrical components, or motors/drives
- a product with incomplete specifications
- a product whose evidence contains conflicting values

The important behavior is that the system should distinguish supported information from inferred or missing information rather than presenting every model output as fact.

## 8. How the AI architecture works

At a high level:

```text
Product Input
     |
     v
Discovery Agent
     |
     v
Evidence Retrieval
     |
     v
Knowledge Decision
     |
     +---- insufficient ----> Research / Acquisition (when allowed)
     |
     v
Intelligence Agent
     |
     v
Normalization + Validation
     |
     +----> Confidence / Conflict Detection
     |
     +----> Field-level Provenance
     |
     v
252-Column Commerce Output
```

The platform deliberately keeps deterministic responsibilities such as normalization, validation, routing signals, and schema mapping outside the LLM whenever practical.

## 9. Why this is different from simple LLM extraction

The system does not simply ask an LLM to fill a JSON object and trust the answer. It builds an evidence-aware product intelligence record.

The key layers are:

- discovery of what is known and missing
- evidence retrieval
- adaptive knowledge decisioning
- targeted acquisition when permitted
- multi-agent enrichment
- schema normalization
- field-level grounding
- confidence and conflict handling
- commerce schema mapping

## 10. Final demonstrated result

The final fresh-product validation run completed successfully for Schneider Electric ATV630U55N4.

Observed result:

```text
Pipeline status: COMPLETED / FINISHED
Populated attributes: 23
Missing information: 1 field
Source conflicts: 0 detected
Evidence chunks: 3
Validation issues shown: 1
```

The UI displayed extracted values including 5.5 kW (7.5 hp), 380–480 V AC, IP21 / UL Type 1, industrial/fluid-management applications, and multiple product features, with field-level provenance snippets.

## 11. Transparency note

The demonstration result still displayed a validation issue/conflict badge and a header-level manufacturer mismatch (`Unknown` in the header while the extracted manufacturer field was Schneider Electric). This is intentionally documented rather than hidden. The platform's value is that such uncertainty is surfaced for review instead of silently converted into false certainty.
