from typing import Dict, Any
from backend.db.models import Product

class ConfidenceService:
    """
    Computes multi-faceted confidence breakdown for product records.
    Exposes confidence structure required by backend logic and AI Engine interfaces.
    """

    def compute_confidence(self, product: Product) -> Dict[str, float]:
        attrs = product.attributes or []
        evidences = product.evidences or []

        # 1. Evidence coverage
        total_attrs = len(attrs)
        attrs_with_evidence = len([a for a in attrs if a.source_snippet])
        evidence_coverage = (attrs_with_evidence / total_attrs * 100.0) if total_attrs > 0 else 50.0

        # 2. Source quality
        source_quality = 95.0 if product.brand and product.sku else 70.0

        # 3. Cross-source agreement
        conflicting_count = len([a for a in attrs if a.competing_value])
        cross_source_agreement = max(100.0 - (conflicting_count * 20.0), 30.0)

        # 4. Validation score
        has_errors = any(i.severity == "critical" for i in product.validation_issues)
        validation_score = 60.0 if has_errors else 98.0

        # Overall composite weighted score
        overall = round(
            (source_quality * 0.25) +
            (evidence_coverage * 0.25) +
            (cross_source_agreement * 0.25) +
            (validation_score * 0.25),
            2
        )

        return {
            "overall": overall,
            "source_quality": round(source_quality, 2),
            "evidence_coverage": round(evidence_coverage, 2),
            "cross_source_agreement": round(cross_source_agreement, 2),
            "validation_score": round(validation_score, 2)
        }

confidence_service = ConfidenceService()
