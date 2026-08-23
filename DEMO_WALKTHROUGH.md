# Live Demo Walkthrough

**Target Time:** ~60 minutes (or time-lapsed if video)
**Objective:** Demonstrate UniHack transforming minimal product inputs into a verified, 252-column commerce record using local AI inference.

---

## 1. Start (The Setup)
**WHAT TO SAY:**
"Welcome to UniHack. Our goal is to solve the massive data friction in B2B commerce. We take partial, messy product identifiers and autonomously turn them into structured, verified, commerce-ready data without hallucinations. We'll run this entirely locally to prove it."

**WHAT TO SHOW:**
Show the clean UniHack upload interface.

## 2. Enter Product & Category
**WHAT TO SAY:**
"Let's imagine a supplier gave us just three pieces of information for an industrial drive."

**WHAT TO SHOW:**
Type in the following:
- **Brand:** Schneider Electric
- **Product:** Altivar Process ATV630
- **Part Number:** ATV630U55N4
- **Category:** Select "Motors & Drives"

## 3. Select Mode & Submit
**WHAT TO SAY:**
"We will select 'LOCAL' mode. This guarantees the data never leaves this machine, using a local Ollama model to ensure absolute privacy for sensitive supply chain data."

**WHAT TO SHOW:**
- Select **LOCAL** processing mode.
- Click **Submit / Process**.

## 4. Explain Pipeline Modal (While Processing)
**WHAT TO SAY:**
"Because we are running a 9-billion parameter model locally to perform deep reasoning, this process takes approximately 60 minutes. It's not a simple autocomplete; it's an autonomous workflow. Let's look at what's happening under the hood."

**WHAT TO SHOW:**
Show the active pipeline modal as it progresses through states.

## 5. Explain Discovery & Evidence
**WHAT TO SAY:**
"First, the Discovery Agent identifies exactly what specs are missing for an 'Altivar Process drive'. Then, the Evidence Retrieval system fetches actual documentation chunks from our local knowledge base. It's building a foundation of truth."

## 6. Explain Knowledge Decision & Intelligence
**WHAT TO SAY:**
"Next, a deterministic Knowledge Decision engine verifies if we have enough evidence to proceed. Since we do, the Intelligence Agent wakes up. Its strict instruction is to extract specs *only* from the retrieved evidence, completely eliminating typical AI hallucinations."

## 7. Explain Normalization, Validation, & Confidence
**WHAT TO SAY:**
"AI outputs are messy, so our deterministic engine normalizes the data. It then strictly validates every single AI-generated claim against the original evidence text. If a claim is explicitly found, it gets a high confidence score. If it contradicts the evidence, it's flagged."

## 8. Explain Provenance & Commerce Output
**WHAT TO SAY:**
"Finally, the data is mapped into our 252-column commerce schema. Every value has provenance—we know exactly which document it came from."

## 9. Show Final Result
*(Wait for processing to complete. The success screen appears.)*

**WHAT TO SAY:**
"The pipeline has finished. As you can see, the status is VERIFIED.
- It populated 23 specific attributes.
- It flagged 1 missing field.
- It found 0 source conflicts.
- All powered by 3 chunks of evidence.

We extracted precise technical specs like '5.5 kW', '380–480 V AC', and 'IP21' strictly from the documentation. Notice the UI correctly surfaces validation issues, such as a manufacturer discrepancy. We don't hide uncertainty; we surface it. This is honest, verifiable product intelligence."

**WHAT TO SHOW:**
- The final Verification screen.
- Scroll through the populated specs.
- Highlight the "Validation Issues (1)" warning to prove honesty.
