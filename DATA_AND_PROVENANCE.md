# Data and Provenance

In B2B industrial commerce, an AI hallucinating a specification can cause catastrophic engineering failures. UniHack treats data provenance as a first-class citizen.

## The Evidence Concept
UniHack does not simply query an LLM and accept its output as truth. Instead, it utilizes an **Evidence Retrieval** phase.
- The system queries connected local knowledge bases or external research tools (when permitted).
- It retrieves discrete "chunks" of text or documentation (e.g., paragraphs from a datasheet or installation manual).
- These chunks are stored immutably as the foundational evidence for the current job.

## Intelligence Synthesis
When the `IntelligenceAgent` extracts data, it is strictly prompted to derive its answers *only* from the retrieved evidence chunks.

## Provenance Tracking
Every single attribute extracted and mapped into the Commerce Schema is traced back to its origin.
- **Source URLs / References:** If a snippet comes from a specific PDF or URL, that metadata is attached to the extracted fact.
- **Attribution:** The system knows exactly which chunk provided the value.

## Missing Data is Honest Data
If the required information is not found in the evidence chunks, the AI is instructed to return `null`.
- We do not silently invent data.
- We do not guess typical values.
- If a source document cannot legally be distributed or accessed, the system will accurately reflect that it lacks the evidence to populate the field.

A dataset with 10% highly verified fields and 90% nulls is exponentially more valuable to a procurement engineer than a dataset with 100% fields populated through AI hallucination.
