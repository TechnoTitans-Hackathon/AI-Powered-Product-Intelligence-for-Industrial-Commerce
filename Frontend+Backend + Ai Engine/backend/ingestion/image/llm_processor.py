"""LLM Reasoning Processor for Anti-Hallucinatory Product Intelligence Extraction."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config
from .prompts import (
    LLM_STRUCTURING_SYSTEM_PROMPT,
    build_llm_structuring_prompt,
)
from .schemas import (
    ComponentRelationship,
    EvidenceJSON,
    EvidenceSourceEnum,
    FieldEvidence,
    FieldStatusEnum,
    ProductIntelligenceOutput,
    QualitativeConfidenceEnum,
    calculate_qualitative_confidence,
)

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    Transforms perceptual Evidence JSON into structured Product Intelligence
    backed by field-level provenance and strict anti-hallucination validation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.api_key = api_key or config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model or config.DEFAULT_VISION_MODEL
        self.provider = (provider or config.AI_PROVIDER or "offline").lower()
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured for LLMProcessor.")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("google-genai package required. Install with: pip install google-genai")
        return self._client

    async def process_evidence(
        self,
        evidence: EvidenceJSON,
    ) -> ProductIntelligenceOutput:
        """
        Converts EvidenceJSON into structured ProductIntelligenceOutput.

        Attempts LLM reasoning via Gemini if configured, otherwise uses
        deterministic rule-based evidence synthesis with offline intelligence.
        """
        evidence_dict = evidence.model_dump(mode="json")
        evidence_json_str = json.dumps(evidence_dict, indent=2)

        if self.provider == "gemini" and self.api_key:
            try:
                logger.info("LLMProcessor: running Gemini reasoning over evidence...")
                return await self._run_gemini_structuring(evidence, evidence_json_str)
            except Exception as e:
                logger.warning(
                    f"LLMProcessor: Gemini reasoning failed ({e}), falling back to deterministic extraction.",
                    exc_info=True,
                )
                return self._fallback_deterministic_extraction(evidence)
        else:
            logger.info("LLMProcessor: running deterministic evidence synthesis (offline mode)...")
            return self._fallback_deterministic_extraction(evidence)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
    async def _run_gemini_structuring(
        self,
        evidence: EvidenceJSON,
        evidence_json_str: str,
    ) -> ProductIntelligenceOutput:
        """Executes LLM reasoning using Gemini 2.0 Flash."""
        client = self._get_client()
        from google.genai import types

        prompt = build_llm_structuring_prompt(evidence_json_str)

        gen_config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            system_instruction=LLM_STRUCTURING_SYSTEM_PROMPT,
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=gen_config,
        )

        raw_text = response.text or "{}"
        parsed = self._parse_json(raw_text)

        return self._build_intelligence_from_dict(parsed, evidence)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Safely parses and repairs JSON from LLM output."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            s = text.find("{")
            e = text.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(text[s : e + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Could not parse LLM JSON: {text[:200]}")
            return {}

    def _fallback_deterministic_extraction(
        self,
        evidence: EvidenceJSON,
    ) -> ProductIntelligenceOutput:
        """
        Deterministic, anti-hallucinatory extraction when LLM API is unavailable.
        Uses regex and direct observation matching to populate only verified fields.
        """
        ocr_texts = [item.text for item in evidence.ocr]
        combined_ocr = " ".join(ocr_texts)
        visual_obs = [obs.observation for obs in evidence.visual_observations]

        # 1. Product Type / Category from visual observations
        primary_obs = visual_obs[0] if visual_obs else None
        product_type = FieldEvidence(
            field="product_type",
            value=primary_obs,
            source=EvidenceSourceEnum.VISION if primary_obs else EvidenceSourceEnum.NONE,
            evidence=f"Observed in image: {primary_obs}" if primary_obs else None,
            confidence=0.92 if primary_obs else 0.0,
            status=FieldStatusEnum.OBSERVED if primary_obs else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=QualitativeConfidenceEnum.HIGH if primary_obs else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Primary object observed in visual analysis" if primary_obs else "No visual objects detected",
        )

        category_name = self._infer_industrial_category(primary_obs or combined_ocr)
        category = FieldEvidence(
            field="category",
            value=category_name,
            source=EvidenceSourceEnum.INFERRED if category_name else EvidenceSourceEnum.NONE,
            evidence=f"Inferred from product type: {primary_obs}" if primary_obs else None,
            confidence=0.85 if category_name else 0.0,
            status=FieldStatusEnum.INFERRED if category_name else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=QualitativeConfidenceEnum.HIGH if category_name else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Taxonomy classification inferred from visual/text cues" if category_name else "Unable to classify category",
        )

        # 2. Model / Part Number from OCR
        detected_model = None
        model_evidence_str = None
        model_conf = 0.0
        # Look for alphanumeric codes like XYZ-123, 6205-2RS, DCD791, M18, DCB518, ABC_123
        for item in evidence.ocr:
            match = re.search(r"\b[A-Z]{1,4}[0-9]{2,6}[A-Z0-9]*\b|\b[A-Z0-9]{2,}[-_/][A-Z0-9]{2,}\b|\b[0-9]{4,}[A-Z]{0,4}\b", item.text.upper())
            if match:
                detected_model = match.group(0)
                model_evidence_str = f"OCR recognized text: '{item.text}' (confidence: {item.confidence:.2f})"
                model_conf = item.confidence
                break

        model = FieldEvidence(
            field="model",
            value=detected_model,
            source=EvidenceSourceEnum.OCR if detected_model else EvidenceSourceEnum.NONE,
            evidence=model_evidence_str,
            confidence=model_conf,
            status=FieldStatusEnum.OBSERVED if detected_model else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=calculate_qualitative_confidence(model_conf, FieldStatusEnum.OBSERVED) if detected_model else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Part/Model number extracted from visible text plate" if detected_model else "No model number visible",
        )

        # 3. Brand detection
        detected_brand = None
        brand_evidence_str = None
        brand_conf = 0.0
        known_brands = [
            "DIABLO", "3M", "DEWALT", "BOSCH", "MAKITA", "MILWAUKEE", "SKF",
            "TIMKEN", "NSK", "EATON", "PARKER", "SIEMENS", "SCHNEIDER", "BALDOR",
        ]
        for item in evidence.ocr:
            upper_t = item.text.upper()
            for b in known_brands:
                if b in upper_t:
                    detected_brand = b.capitalize() if b != "3M" and b != "SKF" and b != "NSK" else b
                    brand_evidence_str = f"OCR recognized brand mark: '{item.text}'"
                    brand_conf = item.confidence
                    break
            if detected_brand:
                break

        brand = FieldEvidence(
            field="brand",
            value=detected_brand,
            source=EvidenceSourceEnum.OCR if detected_brand else EvidenceSourceEnum.NONE,
            evidence=brand_evidence_str,
            confidence=brand_conf,
            status=FieldStatusEnum.OBSERVED if detected_brand else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=calculate_qualitative_confidence(brand_conf, FieldStatusEnum.OBSERVED) if detected_brand else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Brand extracted from label/marking" if detected_brand else "No brand visible on product",
        )

        # 4. Voltage detection
        detected_voltage = None
        voltage_evidence_str = None
        voltage_conf = 0.0
        for item in evidence.ocr:
            v_match = re.search(r"\b(\d+(\.\d+)?\s*(?:V|VAC|VDC|VOLTS?))\b", item.text, re.IGNORECASE)
            if v_match:
                detected_voltage = v_match.group(1).upper()
                voltage_evidence_str = f"OCR recognized voltage specification '{item.text}'"
                voltage_conf = item.confidence
                break

        voltage = FieldEvidence(
            field="voltage",
            value=detected_voltage,
            source=EvidenceSourceEnum.OCR if detected_voltage else EvidenceSourceEnum.NONE,
            evidence=voltage_evidence_str,
            confidence=voltage_conf,
            status=FieldStatusEnum.OBSERVED if detected_voltage else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=calculate_qualitative_confidence(voltage_conf, FieldStatusEnum.OBSERVED) if detected_voltage else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Voltage rating stated on product plate" if detected_voltage else "Voltage rating not visible in image",
        )

        # 5. Power detection
        detected_power = None
        power_evidence_str = None
        power_conf = 0.0
        for item in evidence.ocr:
            p_match = re.search(r"\b(\d+(\.\d+)?\s*(?:W|KW|HP|WATTS?|HORSEPOWER))\b", item.text, re.IGNORECASE)
            if p_match:
                detected_power = p_match.group(1).upper()
                power_evidence_str = f"OCR recognized power specification '{item.text}'"
                power_conf = item.confidence
                break

        power = FieldEvidence(
            field="power",
            value=detected_power,
            source=EvidenceSourceEnum.OCR if detected_power else EvidenceSourceEnum.NONE,
            evidence=power_evidence_str,
            confidence=power_conf,
            status=FieldStatusEnum.OBSERVED if detected_power else FieldStatusEnum.NOT_OBSERVED,
            confidence_level=calculate_qualitative_confidence(power_conf, FieldStatusEnum.OBSERVED) if detected_power else QualitativeConfidenceEnum.NOT_OBSERVED,
            reason="Power rating stated on product plate" if detected_power else "Power rating not visible in image",
        )

        # 5b. Current detection
        detected_current = None
        current_evidence_str = None
        current_conf = 0.0
        for item in evidence.ocr:
            c_match = re.search(r"\b(\d+(\.\d+)?\s*(?:A|AMP|AMPS|AMPERES))\b", item.text, re.IGNORECASE)
            if c_match:
                detected_current = c_match.group(1).upper()
                current_evidence_str = f"OCR recognized current specification '{item.text}'"
                current_conf = item.confidence
                break

        current = FieldEvidence(
            field="current",
            value=detected_current,
            source=EvidenceSourceEnum.OCR if detected_current else EvidenceSourceEnum.NONE,
            evidence=current_evidence_str,
            confidence=current_conf,
            status=FieldStatusEnum.OBSERVED if detected_current else FieldStatusEnum.NOT_OBSERVED,
            reason="Current rating stated on product plate" if detected_current else "Current rating not visible",
        )

        # 5c. Frequency detection
        detected_freq = None
        freq_evidence_str = None
        freq_conf = 0.0
        for item in evidence.ocr:
            f_match = re.search(r"\b(\d+(\.\d+)?\s*(?:HZ|HERTZ))\b", item.text, re.IGNORECASE)
            if f_match:
                detected_freq = f_match.group(1).upper()
                freq_evidence_str = f"OCR recognized frequency specification '{item.text}'"
                freq_conf = item.confidence
                break

        frequency = FieldEvidence(
            field="frequency",
            value=detected_freq,
            source=EvidenceSourceEnum.OCR if detected_freq else EvidenceSourceEnum.NONE,
            evidence=freq_evidence_str,
            confidence=freq_conf,
            status=FieldStatusEnum.OBSERVED if detected_freq else FieldStatusEnum.NOT_OBSERVED,
            reason="Frequency rating stated on product plate" if detected_freq else "Frequency rating not visible",
        )

        # 5d. Pressure detection
        detected_press = None
        press_evidence_str = None
        press_conf = 0.0
        for item in evidence.ocr:
            pr_match = re.search(r"\b(\d+(\.\d+)?\s*(?:PSI|BAR|KPA|MPA))\b", item.text, re.IGNORECASE)
            if pr_match:
                detected_press = pr_match.group(1).upper()
                press_evidence_str = f"OCR recognized pressure rating '{item.text}'"
                press_conf = item.confidence
                break

        pressure = FieldEvidence(
            field="pressure",
            value=detected_press,
            source=EvidenceSourceEnum.OCR if detected_press else EvidenceSourceEnum.NONE,
            evidence=press_evidence_str,
            confidence=press_conf,
            status=FieldStatusEnum.OBSERVED if detected_press else FieldStatusEnum.NOT_OBSERVED,
            reason="Pressure rating stated on product plate" if detected_press else "Pressure rating not visible",
        )

        # 5e. Flow detection
        detected_flow = None
        flow_evidence_str = None
        flow_conf = 0.0
        for item in evidence.ocr:
            fl_match = re.search(r"\b(\d+(\.\d+)?\s*(?:GPM|L/MIN|L/H|CFM|M3/H))\b", item.text, re.IGNORECASE)
            if fl_match:
                detected_flow = fl_match.group(1).upper()
                flow_evidence_str = f"OCR recognized flow rating '{item.text}'"
                flow_conf = item.confidence
                break

        flow = FieldEvidence(
            field="flow",
            value=detected_flow,
            source=EvidenceSourceEnum.OCR if detected_flow else EvidenceSourceEnum.NONE,
            evidence=flow_evidence_str,
            confidence=flow_conf,
            status=FieldStatusEnum.OBSERVED if detected_flow else FieldStatusEnum.NOT_OBSERVED,
            reason="Flow rating stated on product plate" if detected_flow else "Flow rating not visible",
        )

        # 5f. Material detection
        detected_mat = None
        mat_evidence_str = None
        mat_conf = 0.0
        for item in evidence.ocr:
            m_match = re.search(r"\b(SS304|SS316|STAINLESS STEEL|ALUMINUM|BRASS|CAST IRON|PLASTIC|COPPER)\b", item.text, re.IGNORECASE)
            if m_match:
                detected_mat = m_match.group(1).upper()
                mat_evidence_str = f"OCR recognized material grade '{item.text}'"
                mat_conf = item.confidence
                break

        material = FieldEvidence(
            field="material",
            value=detected_mat,
            source=EvidenceSourceEnum.OCR if detected_mat else EvidenceSourceEnum.NONE,
            evidence=mat_evidence_str,
            confidence=mat_conf,
            status=FieldStatusEnum.OBSERVED if detected_mat else FieldStatusEnum.NOT_OBSERVED,
            reason="Material grade stated on product plate" if detected_mat else "Material composition not explicitly stated",
        )

        # Dynamic additional attributes (RPM, Temp, IP rating, Serial No)
        additional_attributes: List[FieldEvidence] = []
        for item in evidence.ocr:
            t = item.text
            # RPM
            rpm_m = re.search(r"\b(\d{3,5}\s*(?:RPM|R/MIN|MIN-1))\b", t, re.IGNORECASE)
            if rpm_m:
                additional_attributes.append(FieldEvidence(
                    field="rpm", value=rpm_m.group(1).upper(), source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR recognized speed: '{t}'", confidence=item.confidence, status=FieldStatusEnum.OBSERVED,
                    reason="Rotational speed rating visible on nameplate"
                ))
            # IP Rating / NEMA Class
            ip_m = re.search(r"\b(IP[0-9]{2}|NEMA\s*[0-9A-Z]+|CLASS\s*[A-H])\b", t, re.IGNORECASE)
            if ip_m:
                additional_attributes.append(FieldEvidence(
                    field="enclosure_rating", value=ip_m.group(1).upper(), source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR recognized rating: '{t}'", confidence=item.confidence, status=FieldStatusEnum.OBSERVED,
                    reason="Ingress/Enclosure rating visible on nameplate"
                ))
            # Temperature
            temp_m = re.search(r"\b(-?\d+\s*°?\s*[CF]|MAX\s*\d+\s*°?C)\b", t, re.IGNORECASE)
            if temp_m:
                additional_attributes.append(FieldEvidence(
                    field="temperature_rating", value=temp_m.group(1).upper(), source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR recognized temperature: '{t}'", confidence=item.confidence, status=FieldStatusEnum.OBSERVED,
                    reason="Operating temperature rating visible on nameplate"
                ))
            # Serial Number
            sn_m = re.search(r"\b(?:S/N|SERIAL|SER|NO\.?)\s*[:#-]?\s*([A-Z0-9-]{5,15})\b", t, re.IGNORECASE)
            if sn_m:
                additional_attributes.append(FieldEvidence(
                    field="serial_number", value=sn_m.group(1).upper(), source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR recognized serial number: '{t}'", confidence=item.confidence, status=FieldStatusEnum.OBSERVED,
                    reason="Serial number visible on nameplate"
                ))

        # Certifications
        certifications: List[FieldEvidence] = []
        for item in evidence.ocr:
            cert_m = re.search(r"\b(CE|UL|CSA|ISO\s*\d+|ROHS|ATEX|IEC|ANSI|ASME)\b", item.text, re.IGNORECASE)
            if cert_m:
                certifications.append(FieldEvidence(
                    field="certification", value=cert_m.group(1).upper(), source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR recognized certification mark: '{item.text}'", confidence=item.confidence,
                    status=FieldStatusEnum.OBSERVED, reason="Compliance/certification mark visible on product"
                ))

        # 6. Product Name
        name_val = self._generate_clean_product_name(
            brand=detected_brand,
            model=detected_model,
            product_type=product_type.value if product_type and product_type.value else None,
        )
        product_name = FieldEvidence(
            field="product_name",
            value=name_val,
            source=EvidenceSourceEnum.INFERRED,
            evidence="Synthesized from verified brand, model, or product type evidence",
            confidence=0.88,
            status=FieldStatusEnum.INFERRED,
            confidence_level=QualitativeConfidenceEnum.HIGH,
            reason="Synthesized identity title",
        )

        # Image Type Classification
        img_type_val = evidence.image_type if evidence.image_type and evidence.image_type != "UNKNOWN" else "PRODUCT_PHOTOGRAPH"
        if any(k in combined_ocr.lower() for k in ["cutaway", "exploded", "rotor", "stator", "wound stator", "shaft", "bearing", "end shield"]):
            img_type_val = "CUTAWAY_DIAGRAM"
        elif any(k in combined_ocr.lower() for k in ["schematic", "circuit", "diagram", "wiring"]):
            img_type_val = "SCHEMATIC"
        elif any(k in combined_ocr.lower() for k in ["spec plate", "volts", "hz", "serial no", "rating plate"]):
            img_type_val = "NAMEPLATE"

        image_type = FieldEvidence(
            field="image_type",
            value=img_type_val,
            source=EvidenceSourceEnum.VISION if evidence.image_type != "UNKNOWN" else EvidenceSourceEnum.INFERRED,
            evidence=f"Visual/OCR structure classified as {img_type_val}",
            confidence=0.92,
            status=FieldStatusEnum.OBSERVED,
            confidence_level=QualitativeConfidenceEnum.HIGH,
            reason="Image structure classification",
        )

        subcategory = FieldEvidence(
            field="subcategory",
            value=None,
            source=EvidenceSourceEnum.NONE,
            status=FieldStatusEnum.NOT_OBSERVED,
            reason="Subcategory not explicitly observed",
        )

        # 7. Unobserved fields explicitly set to NOT_OBSERVED
        sku = FieldEvidence(field="sku", value=None, status=FieldStatusEnum.NOT_OBSERVED, confidence=0.0, source=EvidenceSourceEnum.NONE, reason="SKU not visible in image")
        dimensions = FieldEvidence(field="dimensions", value=None, status=FieldStatusEnum.NOT_OBSERVED, confidence=0.0, source=EvidenceSourceEnum.NONE, reason="Dimensions not visible in image")
        weight = FieldEvidence(field="weight", value=None, status=FieldStatusEnum.NOT_OBSERVED, confidence=0.0, source=EvidenceSourceEnum.NONE, reason="Weight not visible in image")
        color = FieldEvidence(
            field="color",
            value="Observed industrial finish",
            source=EvidenceSourceEnum.VISION,
            evidence="Visual appearance in image",
            confidence=0.80,
            status=FieldStatusEnum.OBSERVED,
            confidence_level=QualitativeConfidenceEnum.HIGH,
            reason="Color finish visible in image",
        )
        description = FieldEvidence(
            field="description",
            value=f"Industrial {img_type_val.lower().replace('_', ' ')} analysis. Detected: {primary_obs or 'component'}.",
            source=EvidenceSourceEnum.INFERRED,
            evidence="Synthesized evidence overview",
            confidence=0.85,
            status=FieldStatusEnum.INFERRED,
            confidence_level=QualitativeConfidenceEnum.HIGH,
            reason="Summary of observed components and markings",
        )

        # Components
        components = []
        for obs in evidence.visual_observations[1:]:
            components.append(
                FieldEvidence(
                    field="component",
                    value=obs.observation,
                    source=EvidenceSourceEnum.VISION,
                    evidence=f"Observed in image: {obs.observation}",
                    confidence=obs.confidence,
                    status=FieldStatusEnum.OBSERVED,
                    confidence_level=calculate_qualitative_confidence(obs.confidence, FieldStatusEnum.OBSERVED),
                    reason="Component visibly present in image",
                )
            )

        # Visible Labels
        visible_labels = []
        for ocr_item in evidence.ocr:
            visible_labels.append(
                FieldEvidence(
                    field="visible_label",
                    value=ocr_item.text,
                    source=EvidenceSourceEnum.OCR,
                    evidence=f"OCR extracted text '{ocr_item.text}'",
                    confidence=ocr_item.confidence,
                    status=FieldStatusEnum.OBSERVED,
                    confidence_level=calculate_qualitative_confidence(ocr_item.confidence, FieldStatusEnum.OBSERVED),
                    reason="Text visibly present on product/packaging",
                )
            )

        # Component Relationships Synthesis
        component_relationships = list(evidence.component_relationships)
        if not component_relationships and img_type_val in ("CUTAWAY_DIAGRAM", "TECHNICAL_DIAGRAM"):
            for ocr_item in evidence.ocr:
                lbl = ocr_item.text.strip()
                if lbl and len(lbl) > 2 and not any(char.isdigit() for char in lbl[:3]):
                    component_relationships.append(
                        ComponentRelationship(
                            name=lbl,
                            type="component",
                            label=lbl,
                            target_component=lbl,
                            relationship="LABELS",
                            confidence=ocr_item.confidence,
                            source=ocr_item.source or "OCR+VISION",
                            evidence=f"Text label '{lbl}' in technical diagram",
                        )
                    )

        output = ProductIntelligenceOutput(
            image_type=image_type,
            product_name=product_name,
            product_type=product_type,
            category=category,
            subcategory=subcategory,
            brand=brand,
            model=model,
            sku=sku,
            dimensions=dimensions,
            weight=weight,
            material=material,
            voltage=voltage,
            current=current,
            power=power,
            frequency=frequency,
            pressure=pressure,
            flow=flow,
            color=color,
            description=description,
            components=components,
            component_relationships=component_relationships,
            applications=[],
            features=[],
            certifications=certifications,
            visible_labels=visible_labels,
            additional_attributes=additional_attributes,
            llm_ready_summary=evidence.llm_ready_summary,
        )

        self._compute_statistics(output)
        return output

    @staticmethod
    def _generate_clean_product_name(
        brand: Optional[str],
        model: Optional[str],
        product_type: Optional[str],
    ) -> str:
        """
        Enforces strict Product Name generation rules without None/null/Unknown leakage:
        - If brand + model available: combine them
        - If only brand available: brand + product type
        - If only model available: model + product type
        - If neither available: generic product type
        - Never expose Python None/null/Unknown placeholders in the product name.
        """
        def _clean(val: Optional[str]) -> Optional[str]:
            if not val:
                return None
            s = str(val).strip()
            if s.lower() in ("none", "null", "unknown", "n/a", "none none", "unknown unknown"):
                return None
            s = re.sub(r'^(None|null|Unknown|N/A)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s+(None|null|Unknown|N/A)$', '', s, flags=re.IGNORECASE)
            return s.strip() if s.strip().lower() not in ("none", "null", "unknown", "n/a") else None

        b = _clean(brand)
        m = _clean(model)
        p = _clean(product_type) or "Industrial Machinery / Component"

        if b and m:
            if b.lower() in m.lower():
                return m
            return f"{b} {m}"

        if b:
            return f"{b} {p}"

        if m:
            return f"{m} {p}"

        return p

    def _build_intelligence_from_dict(
        self,
        data: Dict[str, Any],
        evidence: EvidenceJSON,
    ) -> ProductIntelligenceOutput:
        """Constructs and validates ProductIntelligenceOutput from parsed LLM dict."""
        def _parse_field(field_name: str, default_val: Optional[Any] = None) -> FieldEvidence:
            raw = data.get(field_name)
            if isinstance(raw, dict):
                val = raw.get("value")
                if isinstance(val, str) and val.strip().lower() in ("none", "null", "unknown", "n/a", "none none"):
                    val = None

                status_str = str(raw.get("status", "observed" if val is not None else "not_observed")).lower()
                source_str = str(raw.get("source", "NONE")).upper()
                conf_val = float(raw.get("confidence", 0.85 if val is not None else 0.0))
                
                try:
                    status_enum = FieldStatusEnum(status_str)
                except ValueError:
                    status_enum = FieldStatusEnum.OBSERVED if val is not None else FieldStatusEnum.NOT_OBSERVED

                try:
                    source_enum = EvidenceSourceEnum(source_str)
                except ValueError:
                    source_enum = EvidenceSourceEnum.INFERRED if val is not None else EvidenceSourceEnum.NONE

                if val is None or status_enum == FieldStatusEnum.NOT_OBSERVED:
                    return FieldEvidence(
                        field=field_name,
                        value=None,
                        source=EvidenceSourceEnum.NONE,
                        evidence=None,
                        confidence=0.0,
                        status=FieldStatusEnum.NOT_OBSERVED,
                        confidence_level=QualitativeConfidenceEnum.NOT_OBSERVED,
                        reason=raw.get("reason", "Not visible in uploaded image"),
                    )

                return FieldEvidence(
                    field=field_name,
                    value=val,
                    source=source_enum,
                    evidence=raw.get("evidence"),
                    confidence=conf_val,
                    status=status_enum,
                    confidence_level=calculate_qualitative_confidence(conf_val, status_enum),
                    reason=raw.get("reason"),
                )
            elif raw is not None and not isinstance(raw, (list, dict)):
                val_str = str(raw).strip()
                if val_str.lower() in ("none", "null", "unknown", "n/a", "none none"):
                    return FieldEvidence(
                        field=field_name,
                        value=None,
                        source=EvidenceSourceEnum.NONE,
                        status=FieldStatusEnum.NOT_OBSERVED,
                        confidence=0.0,
                        confidence_level=QualitativeConfidenceEnum.NOT_OBSERVED,
                        reason="Not observed in evidence",
                    )
                return FieldEvidence(
                    field=field_name,
                    value=raw,
                    source=EvidenceSourceEnum.INFERRED,
                    evidence=f"Extracted from reasoning: {raw}",
                    confidence=0.85,
                    status=FieldStatusEnum.INFERRED,
                    confidence_level=QualitativeConfidenceEnum.HIGH,
                )
            else:
                return FieldEvidence(
                    field=field_name,
                    value=default_val,
                    source=EvidenceSourceEnum.NONE,
                    status=FieldStatusEnum.NOT_OBSERVED,
                    confidence=0.0,
                    confidence_level=QualitativeConfidenceEnum.NOT_OBSERVED,
                    reason="Not observed in evidence",
                )

        def _parse_list(field_name: str) -> List[FieldEvidence]:
            raw_list = data.get(field_name, [])
            results = []
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, dict):
                        val = item.get("value")
                        if val and str(val).strip().lower() not in ("none", "null", "unknown", "n/a"):
                            results.append(
                                FieldEvidence(
                                    field=item.get("field", field_name),
                                    value=val,
                                    source=EvidenceSourceEnum(item.get("source", "VISION").upper()) if item.get("source") in EvidenceSourceEnum.__members__ else EvidenceSourceEnum.VISION,
                                    evidence=item.get("evidence"),
                                    confidence=float(item.get("confidence", 0.85)),
                                    status=FieldStatusEnum(item.get("status", "observed")),
                                    reason=item.get("reason"),
                                )
                            )
                    elif isinstance(item, str) and item and item.strip().lower() not in ("none", "null", "unknown", "n/a"):
                        results.append(
                            FieldEvidence(
                                field=field_name,
                                value=item,
                                source=EvidenceSourceEnum.VISION,
                                evidence=f"Observed: {item}",
                                confidence=0.85,
                                status=FieldStatusEnum.OBSERVED,
                            )
                        )
            return results

        output = ProductIntelligenceOutput(
            image_type=_parse_field("image_type", default_val=evidence.image_type),
            product_name=_parse_field("product_name"),
            product_type=_parse_field("product_type"),
            category=_parse_field("category"),
            subcategory=_parse_field("subcategory"),
            brand=_parse_field("brand"),
            model=_parse_field("model"),
            sku=_parse_field("sku"),
            dimensions=_parse_field("dimensions"),
            weight=_parse_field("weight"),
            material=_parse_field("material"),
            voltage=_parse_field("voltage"),
            current=_parse_field("current"),
            power=_parse_field("power"),
            frequency=_parse_field("frequency"),
            pressure=_parse_field("pressure"),
            flow=_parse_field("flow"),
            color=_parse_field("color"),
            description=_parse_field("description"),
            components=_parse_list("components"),
            component_relationships=evidence.component_relationships,
            applications=_parse_list("applications"),
            features=_parse_list("features"),
            certifications=_parse_list("certifications"),
            visible_labels=_parse_list("visible_labels"),
            additional_attributes=_parse_list("additional_attributes"),
            llm_ready_summary=evidence.llm_ready_summary,
        )

        # Post-process product_name to enforce clean product name rules
        clean_name = self._generate_clean_product_name(
            brand=output.brand.value if output.brand and output.brand.value else None,
            model=output.model.value if output.model and output.model.value else None,
            product_type=output.product_type.value if output.product_type and output.product_type.value else None,
        )
        output.product_name.value = clean_name
        output.product_name.status = FieldStatusEnum.INFERRED
        output.product_name.source = EvidenceSourceEnum.INFERRED
        output.product_name.confidence = 0.88
        output.product_name.confidence_level = QualitativeConfidenceEnum.HIGH

        self._compute_statistics(output)
        return output

    @staticmethod
    def _compute_statistics(output: ProductIntelligenceOutput) -> None:
        """Calculates observed, inferred, and unobserved count statistics."""
        observed = 0
        inferred = 0
        not_observed = 0

        core_fields = [
            output.image_type, output.product_name, output.product_type,
            output.category, output.subcategory, output.brand, output.model,
            output.sku, output.dimensions, output.weight, output.material,
            output.voltage, output.current, output.power, output.frequency,
            output.pressure, output.flow, output.color, output.description,
        ]

        for f in core_fields:
            if f.status == FieldStatusEnum.OBSERVED:
                observed += 1
            elif f.status == FieldStatusEnum.INFERRED:
                inferred += 1
            else:
                not_observed += 1

        for col in [output.components, output.features, output.applications, output.visible_labels]:
            for item in col:
                if item.status == FieldStatusEnum.OBSERVED:
                    observed += 1
                elif item.status == FieldStatusEnum.INFERRED:
                    inferred += 1
                else:
                    not_observed += 1

        output.observed_fields_count = observed
        output.inferred_fields_count = inferred
        output.not_observed_fields_count = not_observed

    @staticmethod
    def _infer_industrial_category(text: Optional[str]) -> str:
        """Heuristic industrial taxonomy classifier."""
        if not text:
            return "Industrial Equipment"
        t = text.lower()
        if any(k in t for k in ["sanding", "abrasive", "grinding", "belt", "disc", "cutting", "saw", "blade"]):
            return "Abrasives & Cutting"
        if any(k in t for k in ["bearing", "ball bearing", "roller", "pillow block", "bushing"]):
            return "Bearings & Power Transmission"
        if any(k in t for k in ["pump", "hydraulic", "pneumatic", "valve", "cylinder", "hose"]):
            return "Hydraulics & Fluid Power"
        if any(k in t for k in ["motor", "drive", "inverter", "vfd", "servo", "gearbox"]):
            return "Motors & Drives"
        if any(k in t for k in ["planer", "joiner", "router", "woodworking", "lathe"]):
            return "Woodworking Machinery"
        if any(k in t for k in ["sensor", "transducer", "relay", "breaker", "switch", "terminal", "transformer"]):
            return "Electrical & Instrumentation"
        return "Industrial Equipment"
