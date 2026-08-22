"""Confidence Engine — signal-based, explainable confidence calculation."""

from __future__ import annotations

import logging

from ai_engine.schemas import (
    ConfidenceResult,
    ConfidenceSignals,
    ConfidenceWeights,
    EvidenceSet,
    FieldStatus,
    FieldValue,
    ProductIntelligenceResult,
    SOURCE_AUTHORITY_WEIGHTS,
    SourceType,
)

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """Calculates field-level and product-level confidence from meaningful signals.

    Does NOT ask an AI to arbitrarily say 'confidence = 95%'.
    Instead uses a formula with configurable, explainable weights.
    """

    def __init__(self, weights: ConfidenceWeights | None = None):
        self.weights = weights or ConfidenceWeights()

    def calculate_field_confidence(
        self,
        field: FieldValue,
        evidence: EvidenceSet,
    ) -> ConfidenceResult:
        """Calculate confidence for a single field."""
        signals = ConfidenceSignals()

        # Signal 1: Source authority
        if field.evidence:
            best_authority = max(
                SOURCE_AUTHORITY_WEIGHTS.get(e.source_type, 0.2)
                for e in field.evidence
            )
            signals.source_authority = best_authority
        else:
            signals.source_authority = 0.1

        # Signal 2: Direct evidence
        if field.status == FieldStatus.DIRECTLY_SUPPORTED:
            signals.direct_evidence = 1.0
        elif field.status == FieldStatus.INFERRED:
            signals.direct_evidence = 0.4
        elif field.status == FieldStatus.CONFLICTING:
            signals.direct_evidence = 0.3
        else:
            signals.direct_evidence = 0.0

        # Signal 3: Evidence quality (average retrieval score)
        if field.evidence:
            signals.evidence_quality = sum(e.score for e in field.evidence) / len(field.evidence)

        # Signal 4: Evidence coverage
        signals.evidence_coverage = evidence.coverage_ratio

        # Signal 5: Cross-source agreement
        if len(field.evidence) >= 2:
            signals.cross_source_agreement = 0.9
        elif len(field.evidence) == 1:
            signals.cross_source_agreement = 0.5
        else:
            signals.cross_source_agreement = 0.0

        # Signal 6: Validation success
        if field.validation_passed is True:
            signals.validation_success = 1.0
        elif field.validation_passed is False:
            signals.validation_success = 0.0
        else:
            signals.validation_success = 0.5  # Not yet validated

        # Signal 7: Inference penalty
        if field.status == FieldStatus.INFERRED:
            signals.inference_penalty = 0.3
        elif field.status == FieldStatus.MISSING:
            signals.inference_penalty = 1.0

        # Signal 8: Conflict penalty
        if field.conflicts:
            signals.conflict_penalty = min(len(field.conflicts) * 0.3, 1.0)

        # Signal 9: Missing context
        if field.value is None:
            signals.missing_context_penalty = 1.0

        # Signal 10: Provisional penalty
        from ai_engine.schemas.base import EvidenceClass
        if field.evidence:
            has_verified = any(getattr(e, 'evidence_class', EvidenceClass.PROVISIONAL) == EvidenceClass.VERIFIED for e in field.evidence)
            if not has_verified:
                signals.provisional_penalty = 1.0

        # Calculate weighted score
        w = self.weights
        positive = (
            signals.source_authority * w.source_authority
            + signals.direct_evidence * w.direct_evidence
            + signals.evidence_quality * w.evidence_quality
            + signals.evidence_coverage * w.evidence_coverage
            + signals.cross_source_agreement * w.cross_source_agreement
            + signals.validation_success * w.validation_success
        )
        negative = (
            signals.inference_penalty * w.inference_penalty
            + signals.conflict_penalty * w.conflict_penalty
            + signals.missing_context_penalty * w.missing_context_penalty
            + signals.provisional_penalty * w.provisional_penalty
        )

        score = max(0.0, min(1.0, positive - negative))

        breakdown = {
            "source_authority": signals.source_authority * w.source_authority,
            "direct_evidence": signals.direct_evidence * w.direct_evidence,
            "evidence_quality": signals.evidence_quality * w.evidence_quality,
            "evidence_coverage": signals.evidence_coverage * w.evidence_coverage,
            "cross_source_agreement": signals.cross_source_agreement * w.cross_source_agreement,
            "validation_success": signals.validation_success * w.validation_success,
            "inference_penalty": -(signals.inference_penalty * w.inference_penalty),
            "conflict_penalty": -(signals.conflict_penalty * w.conflict_penalty),
            "missing_context_penalty": -(signals.missing_context_penalty * w.missing_context_penalty),
            "provisional_penalty": -(signals.provisional_penalty * w.provisional_penalty),
        }

        explanation = self._explain(signals, breakdown, score)

        return ConfidenceResult(
            score=round(score, 4),
            signals=signals,
            weights_used=self.weights,
            explanation=explanation,
            breakdown=breakdown,
        )

    def calculate_product_confidence(
        self,
        result: ProductIntelligenceResult,
        evidence: EvidenceSet,
    ) -> float:
        """Calculate and update confidence for all fields in a product result."""
        all_fields = self._collect_fields(result)
        scores = []

        for field in all_fields:
            if field is None:
                continue
            conf = self.calculate_field_confidence(field, evidence)
            field.confidence = conf.score
            scores.append(conf.score)

        overall = sum(scores) / len(scores) if scores else 0.0
        result.overall_confidence = round(overall, 4)
        return overall

    @staticmethod
    def _collect_fields(result: ProductIntelligenceResult) -> list[FieldValue | None]:
        fields: list[FieldValue | None] = [
            result.short_description, result.long_description,
            result.marketing_description, result.retail_description,
            result.applications, result.standards_approvals,
            result.warranty,
        ]
        fields.extend(result.features)
        fields.extend(result.attributes)
        return fields

    @staticmethod
    def _explain(signals: ConfidenceSignals, breakdown: dict, score: float) -> str:
        parts = []
        if signals.source_authority >= 0.9:
            parts.append("High source authority (manufacturer document)")
        elif signals.source_authority >= 0.7:
            parts.append("Moderate source authority")
        else:
            parts.append("Low source authority")

        if signals.direct_evidence >= 0.8:
            parts.append("directly supported by evidence")
        elif signals.direct_evidence >= 0.3:
            parts.append("partially supported")
        else:
            parts.append("no direct evidence")

        if signals.conflict_penalty > 0:
            parts.append(f"conflict penalty applied ({signals.conflict_penalty:.1f})")

        if signals.inference_penalty > 0.2:
            parts.append("inference penalty applied")

        return f"Confidence {score:.0%}: " + "; ".join(parts) + "."
