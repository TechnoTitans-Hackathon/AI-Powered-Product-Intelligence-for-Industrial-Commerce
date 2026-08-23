# Validation and Confidence

UniHack fundamentally separates AI generation from data validation.
**AI generation ≠ evidence. AI generation ≠ validation. AI generation ≠ truth.**

## Deterministic Validation
After the AI extracts product specifications, those claims are pushed through a strict, deterministic rule engine. The engine cross-references the AI's claims against the original text of the retrieved Evidence Chunks.

Every field is assigned a validation status:

- **DIRECTLY_SUPPORTED:** The exact fact or value was explicitly found in the evidence text.
- **INFERRED:** The fact is heavily implied by the evidence, but not explicitly stated in exact terms.
- **MISSING:** The evidence does not contain the fact.
- **CONFLICT:** The AI extracted a fact that actively contradicts the evidence.

## Confidence Scoring
Based on the validation state, the system assigns a mathematically derived confidence score to the entire product record.

- High ratios of `DIRECTLY_SUPPORTED` fields yield high confidence.
- High ratios of `INFERRED` or `MISSING` fields lower the confidence.
- `CONFLICT` fields immediately flag the record for human review.

## Transparent Uncertainty
UniHack is designed to surface uncertainty. If the validation engine detects a mismatch (e.g., the AI extracted a generic manufacturer name, but the evidence explicitly names a subsidiary), the pipeline will still complete as **VERIFIED**, but the UI will display a **Validation Issue**.

We prefer exposing an imperfect, highly-confident subset of data over hiding conflicts behind an illusion of perfect AI accuracy.
