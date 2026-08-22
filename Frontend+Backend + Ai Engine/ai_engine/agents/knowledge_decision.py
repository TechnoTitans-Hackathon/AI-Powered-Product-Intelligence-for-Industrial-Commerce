"""Knowledge Decision Engine — determines whether evidence is sufficient."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ai_engine.schemas.discovery import KnowledgeDecision

from ai_engine.schemas import (
    DiscoveryResult,
    EvidenceSet,
    EvidenceSufficiency,
    SourceType,
)

logger = logging.getLogger(__name__)

# Configurable thresholds
DEFAULT_THRESHOLDS = {
    "min_evidence_count": 1,
    "min_average_score": 0.50,
    "min_coverage_ratio": 0.30,
    "require_manufacturer_source": False,
    "max_conflict_ratio": 0.30,
    "identity_confidence_threshold": 0.40,
}


class KnowledgeDecisionEngine:
    """Determines whether the system has enough evidence to proceed.

    Uses deterministic rules first, then optionally AI for semantic assessment.
    This is one of the most important parts of the innovation — the system
    does not automatically send every request to web search.
    """

    def __init__(self, thresholds: dict[str, Any] | None = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def evaluate(
        self,
        discovery: DiscoveryResult,
        evidence: EvidenceSet,
    ) -> 'KnowledgeDecision':
        """Evaluate evidence sufficiency using deterministic rules.

        Returns:
            KnowledgeDecision containing structured decision logic, missing fields,
            and an adaptive research plan if required.
        """
        from ai_engine.schemas.discovery import KnowledgeDecision
        
        logger.info(f"KnowledgeDecision: evaluating evidence for {discovery.request_id}")
        
        decision = EvidenceSufficiency.SUFFICIENT
        reason = "Evidence meets all requirements for extraction."
        coverage = 1.0
        missing_critical = []
        
        # Determine coverage early
        if len(discovery.required_attributes) > 0:
            coverage = self._estimate_coverage(discovery.required_attributes, evidence)
            evidence.coverage_ratio = coverage
            missing_critical = discovery.missing_information
            
        # Rule 1: Identity uncertain
        if discovery.product_identity.confidence < self.thresholds["identity_confidence_threshold"]:
            decision = EvidenceSufficiency.IDENTITY_UNCERTAIN
            reason = "Low confidence in product identity matching."
            logger.info("KnowledgeDecision: IDENTITY_UNCERTAIN")

        # Rule 2: No evidence at all
        elif evidence.total_sources == 0:
            decision = EvidenceSufficiency.RESEARCH_REQUIRED
            reason = "No baseline evidence found. Full targeted research required."
            logger.info("KnowledgeDecision: RESEARCH_REQUIRED — no evidence")

        # Rule 3: Below minimum evidence count
        elif evidence.total_sources < self.thresholds["min_evidence_count"]:
            decision = EvidenceSufficiency.INSUFFICIENT
            reason = f"Only found {evidence.total_sources} sources. Min required is {self.thresholds['min_evidence_count']}."
            logger.info("KnowledgeDecision: INSUFFICIENT — below min evidence count")

        # Rule 4: Evidence quality too low
        elif evidence.average_score < self.thresholds["min_average_score"]:
            decision = EvidenceSufficiency.INSUFFICIENT
            reason = f"Average evidence score ({evidence.average_score:.2f}) is below threshold."
            logger.info("KnowledgeDecision: INSUFFICIENT — low average score")

        # Rule 5: Coverage ratio check
        elif len(discovery.required_attributes) > 0 and coverage < self.thresholds["min_coverage_ratio"]:
            decision = EvidenceSufficiency.RESEARCH_REQUIRED
            reason = f"Evidence coverage ratio ({coverage:.2f}) is insufficient for critical attributes."
            logger.info(f"KnowledgeDecision: RESEARCH_REQUIRED — coverage {coverage:.2f}")

        # Rule 6: Check for conflicts
        else:
            conflict_signals = self._detect_conflict_signals(evidence)
            if conflict_signals > self.thresholds["max_conflict_ratio"]:
                decision = EvidenceSufficiency.CONFLICTING
                reason = "Conflicting evidence sources detected across critical features."
                logger.info(f"KnowledgeDecision: CONFLICTING — conflict ratio {conflict_signals:.2f}")
            else:
                from ai_engine.schemas.base import EvidenceClass
                has_verified = any(getattr(e, 'evidence_class', EvidenceClass.PROVISIONAL) == EvidenceClass.VERIFIED for e in evidence.evidence)
                if not has_verified and evidence.total_sources > 0:
                    logger.info("KnowledgeDecision: SUFFICIENT — but relying entirely on PROVISIONAL evidence")
                else:
                    logger.info("KnowledgeDecision: SUFFICIENT")

        # Generate adaptive research plan based on the outcome
        research_plan = self.generate_research_plan(discovery, decision)
        
        # Build evidence summary
        summary = None
        if evidence.total_sources > 0:
            summary = f"Found {evidence.total_sources} sources. Top source: {evidence.evidence[0].source_type.value}"

        return KnowledgeDecision(
            decision=decision,
            missing_critical_fields=missing_critical,
            evidence_coverage=coverage,
            reason=reason,
            research_plan=research_plan,
            relevant_evidence_summary=summary
        )

    def _estimate_coverage(
        self,
        required_attributes: list[str],
        evidence: EvidenceSet,
    ) -> float:
        """Estimate what proportion of required attributes are covered by evidence."""
        if not required_attributes:
            return 1.0

        all_text = " ".join(e.content.lower() for e in evidence.evidence)
        covered = 0
        for attr in required_attributes:
            if isinstance(attr, dict):
                attr = attr.get('field', str(attr))
            elif not isinstance(attr, str):
                attr = str(attr)
            # Simple keyword matching — production would use semantic matching
            attr_lower = attr.lower()
            keywords = attr_lower.replace("_", " ").split()
            if any(kw in all_text for kw in keywords):
                covered += 1

        return covered / len(required_attributes)

    @staticmethod
    def _detect_conflict_signals(evidence: EvidenceSet) -> float:
        """Detect potential conflicts in evidence (heuristic)."""
        if len(evidence.evidence) < 2:
            return 0.0

        # Look for source type diversity as a proxy for conflict risk
        types = set(e.source_type for e in evidence.evidence)
        if SourceType.DISTRIBUTOR_DOCUMENT in types and SourceType.MANUFACTURER_DOCUMENT in types:
            # Mix of manufacturer and distributor sources raises conflict risk
            return 0.15
        return 0.05

    def generate_research_plan(
        self,
        discovery: DiscoveryResult,
        sufficiency: EvidenceSufficiency,
    ) -> list[dict[str, Any]]:
        """Generate targeted research requests based on what's missing.

        Returns a list of research targets, not generic queries.
        """
        if sufficiency == EvidenceSufficiency.SUFFICIENT:
            return []

        targets = []
        part = discovery.product_identity.part_number or ""
        mfr = discovery.product_identity.manufacturer or ""
        brand = discovery.product_identity.brand or ""

        for req in discovery.evidence_requirements:
            target = {
                "query": f"{mfr} {part} {req.attribute}".strip(),
                "target_attributes": [req.attribute],
                "priority": req.importance,
                "preferred_source_types": [
                    SourceType.MANUFACTURER_DOCUMENT.value,
                    SourceType.MANUFACTURER_WEBSITE.value,
                ],
            }
            targets.append(target)

        # Add general product specification search if needed
        if sufficiency == EvidenceSufficiency.RESEARCH_REQUIRED:
            targets.insert(0, {
                "query": f"{brand} {part} technical specifications datasheet".strip(),
                "target_attributes": discovery.missing_information[:5],
                "priority": "HIGH",
                "preferred_source_types": [
                    SourceType.MANUFACTURER_DOCUMENT.value,
                ],
            })

        return targets
