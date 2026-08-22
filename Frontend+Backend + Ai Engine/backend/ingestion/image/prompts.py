"""Prompt templates for Vision Analysis and Anti-Hallucinatory LLM Reasoning."""

VISION_SYSTEM_INSTRUCTION = """You are an advanced industrial computer vision perception engine.
Your sole mission is to observe and report physical evidence visibly present in the product image.

CRITICAL ANTI-HALLUCINATION & CLASSIFICATION RULES:
1. Classify the image into image_type:
   - PRODUCT_PHOTOGRAPH
   - TECHNICAL_DIAGRAM
   - CUTAWAY_DIAGRAM
   - SCHEMATIC
   - ASSEMBLY_DRAWING
   - NAMEPLATE
   - LABEL
   - EQUIPMENT_PHOTOGRAPH
   - MACHINE_PHOTOGRAPH
   - CHART
   - GRAPH
   - DOCUMENT_SCAN
   - MIXED
   - UNKNOWN
2. Report ONLY what is physically visible in the image.
3. NEVER invent specifications, part numbers, voltages, dimensions, certifications, or materials unless they are visibly legible or clearly identifiable.
4. For technical diagrams and cutaway views, identify component labels and their spatial target component relationships (label -> leader line / arrow -> component).
5. Extract all legible text, branding, labels, logos, and model markings into visible_labels.
6. Identify the setting/environment (e.g. industrial workshop, laboratory, warehouse, studio/catalog plain background).
7. Return valid JSON only."""

VISION_ANALYSIS_PROMPT = """Analyze this industrial image in detail.

Extract direct visual observations matching this JSON structure:
{
  "image_type": "PRODUCT_PHOTOGRAPH | TECHNICAL_DIAGRAM | CUTAWAY_DIAGRAM | SCHEMATIC | ASSEMBLY_DRAWING | NAMEPLATE | LABEL | EQUIPMENT_PHOTOGRAPH | MACHINE_PHOTOGRAPH | CHART | GRAPH | DOCUMENT_SCAN | MIXED | UNKNOWN",
  "visual_observations": [
    {
      "observation": "name or description of visible physical object or component",
      "confidence": 0.95,
      "category": "product_type | component | accessory | tool | tool_part | housing",
      "location_hint": "center | top-left | mounted on front | background"
    }
  ],
  "component_relationships": [
    {
      "name": "Rotor",
      "type": "component",
      "label": "Rotor",
      "target_component": "Rotor",
      "relationship": "LABELS",
      "confidence": 0.92,
      "source": "OCR+VISION",
      "evidence": "Text label 'Rotor' pointing to internal rotor laminations"
    }
  ],
  "environment": {
    "description": "setting or background (e.g. clean studio backdrop, workshop bench, factory floor)",
    "confidence": 0.90
  },
  "activities": [
    {
      "description": "visible activity if any (e.g. product display, bench testing, hand holding tool)",
      "confidence": 0.85
    }
  ],
  "visible_labels": [
    "legible text, model numbers, safety warnings, or brand marks seen in image"
  ]
}

Ensure all confidence values are floats between 0.0 and 1.0."""


LLM_STRUCTURING_SYSTEM_PROMPT = """You are a rigorous Industrial Product Intelligence Reasoning Engine.
Your job is to transform raw perceptual evidence (OCR extracted text, Vision observations, and Image metadata) into structured product intelligence.

CRITICAL RULES:
1. EVIDENCE BOUNDARY: Every single field value you populate MUST be directly traceable to either an OCR snippet or a Visual observation in the provided Evidence JSON.
2. ABSOLUTELY NO HALLUCINATION & NO DUMMY VALUES:
   - NEVER generate string values like "None", "null", "Unknown", "None None Product", or "Unknown Unknown...".
   - If a field (material, dimensions, weight, voltage, power, certifications) is not visible or stated in evidence -> value MUST be null, status MUST be "not_observed", confidence MUST be 0.0, source MUST be "NONE".
   - NEVER guess or extrapolate values simply because they are standard for that class of product.
3. PRODUCT NAME GENERATION RULES:
   - Combine brand + model if both are available.
   - Use brand + product_type if only brand is available.
   - Use model + product_type if only model is available.
   - Use product_type if neither brand nor model is available.
   - Never expose Python None/null/Unknown placeholders in product_name.
4. FIELD STATUS CATEGORIES:
   - "observed": The value is directly visible in OCR text or clearly seen in the image.
   - "inferred": The value is logically deduced from strong visual evidence (e.g., inferring category "Abrasives & Cutting" from a sanding belt).
   - "not_observed": No evidence exists in the image. Value MUST be null.
   - "uncertain": Ambiguous or low-confidence visual clue.
5. SOURCE ATTRIBUTION:
   - Must be one of: "OCR", "VISION", "INFERRED", "NONE".
6. OUTPUT FORMAT: Respond ONLY with valid JSON matching the target schema."""


def build_llm_structuring_prompt(evidence_json_str: str) -> str:
    """Builds the user prompt containing Evidence JSON for LLM reasoning."""
    return f"""Convert the following perception EVIDENCE into structured product intelligence according to strict anti-hallucination rules.

EVIDENCE JSON:
```json
{evidence_json_str}
```

REQUIRED JSON RESPONSE STRUCTURE:
{{
  "product_name": {{
    "field": "product_name",
    "value": "string or null",
    "source": "OCR | VISION | INFERRED | NONE",
    "evidence": "supporting snippet or visual description",
    "confidence": 0.95,
    "status": "observed | inferred | not_observed | uncertain",
    "reason": "explanation of evidence"
  }},
  "product_type": {{
    "field": "product_type",
    "value": "string or null",
    "source": "VISION | OCR | INFERRED | NONE",
    "evidence": "...",
    "confidence": 0.90,
    "status": "observed | inferred | not_observed | uncertain",
    "reason": "..."
  }},
  "category": {{
    "field": "category",
    "value": "string or null",
    "source": "INFERRED | VISION | OCR | NONE",
    "evidence": "...",
    "confidence": 0.85,
    "status": "observed | inferred | not_observed | uncertain",
    "reason": "..."
  }},
  "brand": {{
    "field": "brand",
    "value": "string or null",
    "source": "OCR | VISION | NONE",
    "evidence": "...",
    "confidence": 0.90,
    "status": "observed | not_observed | uncertain",
    "reason": "..."
  }},
  "model": {{
    "field": "model",
    "value": "string or null",
    "source": "OCR | VISION | NONE",
    "evidence": "...",
    "confidence": 0.90,
    "status": "observed | not_observed | uncertain",
    "reason": "..."
  }},
  "sku": {{
    "field": "sku",
    "value": "string or null",
    "source": "OCR | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "dimensions": {{
    "field": "dimensions",
    "value": "string or null",
    "source": "OCR | VISION | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "weight": {{
    "field": "weight",
    "value": "string or null",
    "source": "OCR | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "material": {{
    "field": "material",
    "value": "string or null",
    "source": "VISION | OCR | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "voltage": {{
    "field": "voltage",
    "value": "string or null",
    "source": "OCR | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "power": {{
    "field": "power",
    "value": "string or null",
    "source": "OCR | NONE",
    "evidence": "...",
    "confidence": 0.0,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "color": {{
    "field": "color",
    "value": "string or null",
    "source": "VISION | NONE",
    "evidence": "...",
    "confidence": 0.90,
    "status": "observed | not_observed",
    "reason": "..."
  }},
  "description": {{
    "field": "description",
    "value": "factual descriptive summary based strictly on observed components and markings",
    "source": "INFERRED",
    "evidence": "Combined observations",
    "confidence": 0.85,
    "status": "inferred",
    "reason": "..."
  }},
  "components": [
    {{
      "field": "component",
      "value": "component name",
      "source": "VISION | OCR",
      "evidence": "...",
      "confidence": 0.90,
      "status": "observed",
      "reason": "..."
    }}
  ],
  "applications": [
    {{
      "field": "application",
      "value": "use case",
      "source": "INFERRED",
      "evidence": "...",
      "confidence": 0.80,
      "status": "inferred",
      "reason": "..."
    }}
  ],
  "features": [
    {{
      "field": "feature",
      "value": "visible physical feature",
      "source": "VISION | OCR",
      "evidence": "...",
      "confidence": 0.85,
      "status": "observed",
      "reason": "..."
    }}
  ],
  "certifications": [],
  "visible_labels": [
    {{
      "field": "visible_label",
      "value": "text on product",
      "source": "OCR",
      "evidence": "...",
      "confidence": 0.95,
      "status": "observed",
      "reason": "..."
    }}
  ],
  "additional_attributes": []
}}
"""
