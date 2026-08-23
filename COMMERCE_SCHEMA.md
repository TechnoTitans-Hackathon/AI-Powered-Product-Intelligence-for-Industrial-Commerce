# The 252-Column Commerce Schema

Industrial B2B platforms (like ERPs, PIMs, and procurement systems) require highly structured, granular data. Simply storing a block of text describing a product is useless for automated commerce.

UniHack forces the AI's messy, probabilistic output into a rigid, deterministic **252-column schema**.

## Logical Families
The 252 columns are grouped into logical families to support deep product filtering and taxonomy matching:

1. **Identity:** Brand, Manufacturer, Part Numbers, GTIN, UPC.
2. **Descriptions:** Short, long, and SEO-optimized marketing copy.
3. **Features & Applications:** Bulleted lists of capabilities and target use-cases.
4. **Technical Attributes:** Voltage, wattage, IP rating, material, tolerances.
5. **UOM (Unit of Measure):** Length, width, weight, operating temperatures.
6. **Packaging:** Box quantities, pallet sizes, shipping weights.
7. **Compliance:** RoHS, REACH, UL, CE markings.
8. **Documentation:** Links to datasheets, installation manuals, safety data sheets.
9. **Images:** URLs for primary product photos and schematics.

## The Power of Null
A single product will rarely, if ever, populate all 252 columns. An industrial drive has voltage and IP ratings; a steel bolt has thread pitch and tensile strength.

- Unused columns remain `null`.
- We do not populate `null` columns with "N/A" or "None".
- Null is preferable to fabricated data. Downstream ERP systems rely on accurate nulls to properly map taxonomy trees.

## Representative Mappings
In our validated Schneider Electric run, UniHack correctly populated fields like:
- `power_rating`: 5.5 kW (7.5 hp)
- `voltage`: 380–480 V AC
- `ip_rating`: IP21 / UL Type 1
- `applications`: Fluid-management applications, Process monitoring and control

The remaining irrelevant columns correctly remained `null`, resulting in a highly accurate, focused dataset.
