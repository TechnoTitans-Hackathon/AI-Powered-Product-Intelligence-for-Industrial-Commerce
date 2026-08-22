"""Output Adapter — converts AI engine results to backend schemas for DB persistence.

AI ENGINE produces ProductIntelligenceResult with full intelligence metadata.
BACKEND needs AIServiceResponse format for database storage via ProductService.

This adapter bridges the gap, preserving all confidence, evidence, provenance,
validation, and explainability information.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


from ai_engine.schemas import (
    FieldStatus,
    FieldValue,
    ProductIntelligenceResult,
    ProcessingStatus,
)
from ai_engine.orchestration.pipeline import PipelineResult

from backend.schemas.ai_contract import AIAttributeItem, AIServiceResponse
from backend.schemas.retrieval import EvidenceSchema

logger = logging.getLogger(__name__)


def _field_status_to_backend_status(status: FieldStatus) -> str:
    """Map AI engine FieldStatus to backend attribute status string."""
    return {
        FieldStatus.DIRECTLY_SUPPORTED: "ai_inferred",
        FieldStatus.INFERRED: "ai_inferred",
        FieldStatus.MISSING: "missing",
        FieldStatus.CONFLICTING: "conflicting",
        FieldStatus.UNKNOWN: "missing",
    }.get(status, "ai_inferred")


def _classify_attribute_type(field_name: str) -> str:
    """Classify an attribute into backend's attribute_type categories.

    Industry-agnostic: uses the attribute name itself, not assumptions
    about what industry the product belongs to.
    """
    name_lower = field_name.lower()

    dimension_keywords = {
        "length", "width", "height", "depth", "diameter", "thickness",
        "weight", "mass", "volume", "size", "dimension",
    }
    material_keywords = {"material", "finish", "coating", "surface"}
    certification_keywords = {
        "standard", "approval", "certification", "ul", "ce",
        "rohs", "energy star", "nema", "atex",
    }

    for kw in dimension_keywords:
        if kw in name_lower:
            return "dimension"
    for kw in material_keywords:
        if kw in name_lower:
            return "material"
    for kw in certification_keywords:
        if kw in name_lower:
            return "certification"

    return "technical_spec"


def intelligence_to_ai_response(
    result: ProductIntelligenceResult,
    pipeline_result: PipelineResult = None,
) -> AIServiceResponse:
    """Convert AI engine's ProductIntelligenceResult to backend's AIServiceResponse.

    This enables the existing ProductService.apply_ai_response() to persist
    the AI engine's output into the backend database without modification.
    """
    identity = result.identity

    # Build product dict matching what apply_ai_response expects
    product_dict: Dict[str, Any] = {
        "name": identity.product_name or identity.part_number or "",
        "sku": identity.part_number or "",
        "brand": identity.brand or "",
        "manufacturer": identity.manufacturer or "",
        "category": identity.category or "",
        "subcategory": identity.fine_class or "",
        "industry": identity.industry or "",
        "description": (
            result.short_description.value
            if result.short_description and result.short_description.value
            else ""
        ),
        "completenessScore": round(result.completeness_ratio * 100, 1),
        "confidenceScore": round(result.overall_confidence * 100, 1),
        "status": (
            "verified"
            if result.processing_status == ProcessingStatus.COMPLETED
            else "processing"
        ),
    }

    # Convert attributes
    attributes: List[AIAttributeItem] = []
    for fv in result.attributes:
        if fv.value is None and fv.status == FieldStatus.MISSING:
            continue  # Don't persist MISSING attributes with no value

        # Extract evidence snippet for this attribute
        snippet = None
        snippet_location = None
        if fv.evidence:
            snippet = fv.evidence[0].snippet if fv.evidence[0].snippet else None
            snippet_location = fv.evidence[0].source if fv.evidence[0].source else None

        # Find competing value if conflicting
        competing = None
        if fv.conflicts:
            competing = fv.conflicts[0].value_b if fv.conflicts else None

        attributes.append(AIAttributeItem(
            key=fv.field_name,
            value=str(fv.value) if fv.value is not None else "",
            normalized_value=str(fv.normalized_value) if fv.normalized_value else None,
            unit=fv.unit,
            attribute_type=_classify_attribute_type(fv.field_name),
            confidence=round(fv.confidence * 100, 1) if fv.confidence <= 1.0 else fv.confidence,
            source_snippet=snippet,
            source_location=snippet_location,
            explanation=fv.reason,
            competing_value=competing,
        ))

    # Convert evidence from the pipeline result
    evidence: List[EvidenceSchema] = []
    if pipeline_result and hasattr(pipeline_result, "all_evidence") and pipeline_result.all_evidence:
        for ev in pipeline_result.all_evidence.evidence:
            evidence.append(EvidenceSchema(
                evidence_id=ev.evidence_id,
                source_id=ev.metadata.get("source_id", "unknown_source"),
                document=ev.metadata.get("document", ev.source),
                source=ev.source,
                url=ev.source_url,
                timestamp=ev.timestamp,
                content=ev.content,
                score=ev.score,
                metadata=ev.metadata
            ))

    # Build confidence dict
    confidence_dict: Dict[str, Any] = {
        "overall": result.overall_confidence,
        "completeness": result.completeness_ratio,
        "fields_total": result.fields_total,
        "fields_populated": result.fields_populated,
        "fields_missing": result.fields_missing,
        "fields_conflicting": result.fields_conflicting,
    }

    # Build explanation
    explanation_dict: Dict[str, Any] = {
        "processing_status": result.processing_status.value,
        "enrichment_version": result.enrichment_version,
        "errors": [
            {"stage": e.get("stage", ""), "error": e.get("error", "")}
            for e in result.errors
        ] if result.errors else [],
    }

    # Determine review requirement
    review_required = (
        result.fields_conflicting > 0
        or result.fields_needing_review > 0
        or result.processing_status != ProcessingStatus.COMPLETED
    )

    return AIServiceResponse(
        product=product_dict,
        attributes=attributes,
        descriptions={
            "short": result.short_description.value if result.short_description else None,
            "long": result.long_description.value if result.long_description else None,
            "marketing": result.marketing_description.value if result.marketing_description else None,
            "retail": result.retail_description.value if result.retail_description else None,
        },
        confidence=confidence_dict,
        sources=[],
        evidence=evidence,
        explanation=explanation_dict,
        validation_hints=[],
        review_required=review_required,
    )


def pipeline_result_to_full_response(
    pipeline_result: PipelineResult,
) -> Dict[str, Any]:
    """Convert the full PipelineResult to a rich API response.

    This is used by the new /products/intelligence endpoint.
    Preserves ALL intelligence, confidence, validation, provenance,
    commerce data, and explainability information.
    """
    intel = pipeline_result.intelligence
    if intel is None:
        return {
            "success": False,
            "errors": [
                {"stage": e.stage, "error": e.message}
                for e in pipeline_result.errors
            ],
            "processing_time_ms": pipeline_result.processing_time_ms,
        }

    identity = intel.identity

    # Build structured attributes list
    structured_attributes = []
    missing_attributes = []
    for fv in intel.attributes:
        attr_dict = {
            "label": fv.field_name,
            "value": fv.value,
            "unit": fv.unit,
            "status": fv.status.value if fv.status else "UNKNOWN",
            "confidence": fv.confidence,
            "evidence_count": len(fv.evidence) if fv.evidence else 0,
            "reason": fv.reason,
        }
        if fv.value is not None and fv.status != FieldStatus.MISSING:
            structured_attributes.append(attr_dict)
        else:
            missing_attributes.append(attr_dict)

    # Build evidence list from discovery
    evidence_list = []
    discovery = pipeline_result.discovery_result
    if discovery:
        for info in getattr(discovery, "known_information", []):
            if isinstance(info, dict):
                evidence_list.append(info)

    # Build conflicts
    conflicts_list = []
    for conflict in intel.conflicts:
        conflicts_list.append({
            "field": conflict.field_name,
            "value_a": conflict.value_a,
            "source_a": conflict.source_a,
            "value_b": conflict.value_b,
            "source_b": conflict.source_b,
            "type": conflict.conflict_type.value if conflict.conflict_type else "unknown",
            "review_required": conflict.review_required,
        })

    # Build validation summary
    validation_summary = None
    if pipeline_result.validation_result:
        vr = pipeline_result.validation_result
        validation_summary = {
            "passed": vr.passed,
            "total_checks": vr.total_checks,
            "passed_checks": vr.passed_checks,
            "failed_checks": vr.failed_checks,
            "warning_checks": vr.warning_checks,
        }

    return {
        "success": pipeline_result.success,
        "request_id": pipeline_result.diagnostics.get("request_id", ""),
        "processing_time_ms": round(pipeline_result.processing_time_ms, 1),

        # Product Identity
        "product_identity": {
            "manufacturer": identity.manufacturer,
            "brand": identity.brand,
            "part_number": identity.part_number,
            "product_name": identity.product_name,
            "category": identity.category,
            "industry": identity.industry,
            "confidence": identity.confidence,
        },

        # Descriptions
        "descriptions": {
            "short": intel.short_description.value if intel.short_description else None,
            "long": intel.long_description.value if intel.long_description else None,
            "marketing": intel.marketing_description.value if intel.marketing_description else None,
            "retail": intel.retail_description.value if intel.retail_description else None,
        },

        # Features
        "features": [
            {
                "text": fv.value,
                "status": fv.status.value if fv.status else "UNKNOWN",
                "confidence": fv.confidence,
            }
            for fv in intel.features
            if fv.value
        ],

        # Attributes
        "structured_attributes": structured_attributes,
        "missing_attributes": missing_attributes,

        # Conflicts
        "conflicts": conflicts_list,

        # Confidence & Validation
        "confidence": {
            "overall": intel.overall_confidence,
            "completeness_ratio": intel.completeness_ratio,
            "fields_total": intel.fields_total,
            "fields_populated": intel.fields_populated,
            "fields_missing": intel.fields_missing,
            "fields_conflicting": intel.fields_conflicting,
            "fields_needing_review": intel.fields_needing_review,
        },
        "validation": validation_summary,

        # Research & Evidence
        "research_performed": pipeline_result.research_performed,
        "evidence_sufficiency": (
            pipeline_result.evidence_sufficiency.value
            if pipeline_result.evidence_sufficiency
            else None
        ),
        "known_information": evidence_list,

        # Human Review
        "human_review_required": (
            intel.fields_conflicting > 0
            or intel.fields_needing_review > 0
        ),

        # Commerce Output
        "commerce_data": pipeline_result.commerce_data or {},

        # Diagnostics
        "diagnostics": pipeline_result.diagnostics,

        # Errors
        "errors": [
            {"stage": e.stage, "error": e.message}
            for e in pipeline_result.errors
        ],
    }


def map_confidence_level(overall_confidence: float, conflict_count: int = 0) -> str:
    """
    Maps a 0.0–1.0 float confidence score to a qualitative level for UI display.

    Rules:
    - CONFLICT: any detected conflicts, regardless of confidence
    - HIGH:   >= 0.75
    - MEDIUM: >= 0.50
    - LOW:    >= 0.25
    - CONFLICT/VERY LOW: < 0.25
    """
    if conflict_count > 0:
        return "CONFLICT"
    if overall_confidence >= 0.75:
        return "HIGH"
    if overall_confidence >= 0.50:
        return "MEDIUM"
    if overall_confidence >= 0.25:
        return "LOW"
    return "CONFLICT"

# ─── Result → Persistence Mapping ─────────────────────────────────────────────

def extract_persistence_data(result: PipelineResult) -> dict[str, Any]:
    """
    Extracts data from a Hackathon PipelineResult into a flat dict
    suitable for updating Techno DB model fields.
    """
    if not result.success or result.intelligence is None:
        return {
            "status": "failed",
            "confidence_level": "CONFLICT",
            "confidence_score": 0.0,
            "completeness_score": 0.0,
            "missing_fields_count": 0,
            "conflict_fields_count": 0,
            "fields_total": 0,
            "fields_populated": 0,
            "intelligence_json": None,
            "commerce_json": None,
        }

    intel = result.intelligence
    conflict_count = intel.fields_conflicting or 0

    return {
        "status": _map_status(result),
        "confidence_level": map_confidence_level(intel.overall_confidence, conflict_count),
        "confidence_score": round(intel.overall_confidence, 4),
        "completeness_score": round(intel.completeness_ratio, 4),
        "missing_fields_count": intel.fields_missing,
        "conflict_fields_count": intel.fields_conflicting,
        "fields_total": intel.fields_total,
        "fields_populated": intel.fields_populated,
        "intelligence_json": _intelligence_to_json(intel),
        "commerce_json": result.commerce_data or {},
    }


def _map_status(result: PipelineResult) -> str:
    """Map PipelineResult to Techno product status string."""
    if not result.success:
        return "failed"
    if result.intelligence is None:
        return "failed"
    intel = result.intelligence
    if intel.fields_conflicting and intel.fields_conflicting > 0:
        return "conflicting"
    if result.validation_result and not result.validation_result.passed:
        return "needs_review"
    return "verified"


def _intelligence_to_json(intel) -> dict[str, Any]:
    """Serialize Hackathon ProductIntelligenceResult to a JSON-compatible dict."""
    try:
        return intel.model_dump(mode="json")
    except Exception:
        return {}


def extract_attributes_from_result(result: PipelineResult) -> list[dict[str, Any]]:
    """
    Extract Hackathon FieldValues into a list of attribute dicts
    for Techno's Attribute model.
    """
    if not result.success or result.intelligence is None:
        return []

    intel = result.intelligence
    attrs = []

    # Dynamic attributes (label/value/unit triplets)
    dim_keywords = {"dimension", "dimensions", "length", "width", "height", "diameter", "bore", "weight", "thickness", "size"}
    mat_keywords = {"material", "materials", "construction", "body material", "housing material"}
    cert_keywords = {"certification", "certifications", "standards", "approvals", "compliance", "standards/approvals"}
    app_keywords = {"application", "applications", "intended use", "use case"}

    for field in intel.attributes:
        if field.value is None and field.status and field.status.value == "MISSING":
            continue

        snippet_text = None
        source_loc = None
        if field.evidence:
            ev = field.evidence[0]
            snippet_text = getattr(ev, "snippet", getattr(ev, "content", ""))
            if snippet_text:
                snippet_text = snippet_text[:500]
            source_loc = getattr(ev, "source", None)

        fn_lower = field.field_name.lower()
        if any(k in fn_lower for k in dim_keywords):
            attr_type = "dimension"
        elif any(k in fn_lower for k in mat_keywords):
            attr_type = "material"
        elif any(k in fn_lower for k in cert_keywords):
            attr_type = "certification"
        elif any(k in fn_lower for k in app_keywords):
            attr_type = "application"
        else:
            attr_type = "technical_spec"

        attrs.append({
            "attribute_type": attr_type,
            "key": field.field_name,
            "value": field.value,
            "normalized_value": field.normalized_value,
            "unit": field.unit,
            "confidence": round(field.confidence, 4),
            "status": "ai_inferred",
            "field_status": field.status.value if field.status else None,
            "source_snippet": snippet_text,
            "source_location": source_loc,
            "explanation": field.reason,
            "competing_value": field.conflicts[0].value_b if field.conflicts else None,
        })


    # Features
    for feat in (intel.features or []):
        if feat.value is None and feat.status and feat.status.value == "MISSING":
            continue
            
        snippet_text = None
        source_loc = None
        if feat.evidence:
            ev = feat.evidence[0]
            snippet_text = getattr(ev, "snippet", getattr(ev, "content", ""))
            if snippet_text:
                snippet_text = snippet_text[:500]
            source_loc = getattr(ev, "source", None)

        attrs.append({
            "attribute_type": "feature",
            "key": "feature",
            "value": feat.value,
            "normalized_value": feat.value,
            "unit": None,
            "confidence": round(feat.confidence, 4),
            "status": "ai_inferred",
            "field_status": feat.status.value if feat.status else None,
            "source_snippet": snippet_text,
            "source_location": source_loc,
            "explanation": feat.reason,
            "competing_value": None,
        })

    return attrs


def extract_evidence_from_result(result: PipelineResult) -> list[dict[str, Any]]:
    """Extract evidence snippets from Hackathon pipeline result."""
    if not result.success or result.intelligence is None:
        return []

    intel = result.intelligence
    evidence_list = []
    seen = set()

    for field in intel.attributes + (intel.features or []):
        for idx, ev in enumerate(field.evidence):
            source_name = getattr(ev, "source", "unknown_source")
            content = getattr(ev, "snippet", getattr(ev, "content", ""))
            key = f"{source_name}_{content[:50]}"
            if key not in seen and content:
                seen.add(key)
                evidence_list.append({
                    "source_id": f"ev_{len(evidence_list)+1}",
                    "document_name": source_name,
                    "url": getattr(ev, "source_url", None),
                    "page": getattr(ev, "page", None),
                    "section": getattr(ev, "section", None),
                    "content": content[:2000],
                    "score": getattr(ev, "score", 0.8),
                    "source_type": ev.source_type.value if hasattr(ev, "source_type") and hasattr(ev.source_type, "value") else str(getattr(ev, "source_type", "")),
                    "provenance_json": {},
                })

    return evidence_list


def extract_validation_issues_from_result(result: PipelineResult) -> list[dict[str, Any]]:
    """Extract validation failures/warnings from Hackathon ValidationResult."""
    issues = []
    if not result.validation_result:
        return issues

    val = result.validation_result
    # Map validation failures
    for failure in getattr(val, "failures", []):
        issues.append({
            "severity": "high",
            "type": "validation_failure",
            "field": str(failure),
            "message": str(failure),
            "current_value": None,
            "suggested_value": None,
        })

    # Map warnings
    for warning in getattr(val, "warnings", []):
        issues.append({
            "severity": "medium",
            "type": "validation_warning",
            "field": str(warning),
            "message": str(warning),
            "current_value": None,
            "suggested_value": None,
        })

    # Map conflicts from intelligence
    if result.intelligence:
        for conflict in result.intelligence.conflicts:
            issues.append({
                "severity": "high",
                "type": "conflict",
                "field": conflict.field_name,
                "message": f"Conflicting values: '{conflict.value_a}' vs '{conflict.value_b}'",
                "current_value": conflict.value_a,
                "suggested_value": conflict.value_b,
                "source_a": conflict.source_a,
                "source_b": conflict.source_b,
            })

    # Map missing fields
    if result.intelligence:
        for attr in result.intelligence.attributes:
            if attr.status and attr.status.value == "MISSING":
                issues.append({
                    "severity": "medium",
                    "type": "missing_field",
                    "field": attr.field_name,
                    "message": f"Field '{attr.field_name}' is missing — no supporting evidence found",
                    "current_value": None,
                    "suggested_value": None,
                })

    return issues
