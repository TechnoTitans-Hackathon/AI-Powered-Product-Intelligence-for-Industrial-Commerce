# Final Validation Proof

The following documents the actual, verified successful run of the UniHack pipeline using the local `qwen3.5:9b-q4_K_M` model.

## Input Parameters
- **Product:** Altivar Process ATV630
- **Brand:** Schneider Electric
- **Part Number:** ATV630U55N4
- **Category:** Motors & Drives
- **Mode:** LOCAL

## Observed Final State
- **Pipeline Status:** `VERIFIED`
- **Populated Fields:** 23
- **Missing Fields:** 1 field
- **Source Conflicts:** 0 detected
- **Evidence Used:** 3 chunks

## Extracted Technical Values
The AI successfully extracted and normalized the following technical specifications strictly from the retrieved evidence:
- **Power Rating:** 5.5 kW (7.5 hp)
- **Voltage:** 380–480 V AC
- **IP Rating:** IP21 / UL Type 1
- **Target Market:** Industrial
- **Applications:** Fluid-management applications, Process monitoring and control, Asset monitoring
- **Features:** Energy-saving Stop and Go, Synchronous motor control, Asynchronous motor control

## Honest Surfacing of Issues
The final UI explicitly displayed:
`Validation Issues (1)`

**Manufacturer Discrepancy:**
The header of the UI showed `Manufacturer = Unknown`, while the AI correctly extracted the underlying field as `manufacturer = Schneider Electric`.

We did not alter the code or the documentation to hide this UI discrepancy. This proves that the pipeline can achieve a `VERIFIED` status for its extracted attributes while still surfacing uncertainty or mismatches to the human reviewer.
