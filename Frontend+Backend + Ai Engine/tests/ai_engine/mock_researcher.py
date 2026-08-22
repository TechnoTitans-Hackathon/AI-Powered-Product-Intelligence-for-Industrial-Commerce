from ai_engine.research.researcher import ResearchInterface
from ai_engine.schemas import (
    Evidence,
    EvidenceSet,
    ResearchRequest,
    ResearchResult,
    ResearchSourceCandidate,
    SourceType,
)
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class MockResearchProvider(ResearchInterface):
    """Mock research provider returning realistic search results."""

    async def research(self, request: ResearchRequest) -> ResearchResult:
        start = time.time()
        logger.info(f"MockResearchProvider: researching '{request.product_name}'")

        candidates: list[ResearchSourceCandidate] = []
        evidence_list: list[Evidence] = []

        part = request.part_number or "UNKNOWN"
        mfr = request.manufacturer or "Unknown"
        name = request.product_name or part

        # Simulate source discovery
        candidates.append(ResearchSourceCandidate(
            url=f"https://www.{mfr.lower().replace(' ', '')}.com/products/{part}",
            title=f"{mfr} - {name} Product Page",
            source_type=SourceType.MANUFACTURER_WEBSITE,
            quality_score=0.90,
            selected=True,
        ))
        candidates.append(ResearchSourceCandidate(
            url=f"https://www.industrialsupply.com/product/{part}",
            title=f"{name} - Industrial Supply Co",
            source_type=SourceType.DISTRIBUTOR_DOCUMENT,
            quality_score=0.70,
            selected=True,
        ))
        candidates.append(ResearchSourceCandidate(
            url=f"https://www.randomforum.com/thread/{part}-review",
            title=f"User review of {name}",
            source_type=SourceType.SECONDARY_SOURCE,
            quality_score=0.30,
            selected=False,
            rejection_reason="Low quality user-generated content",
        ))

        # Generate evidence from selected sources
        for target in request.targets:
            evidence_list.append(Evidence(
                evidence_id=f"ev_research_{uuid.uuid4().hex[:8]}",
                content=f"Research finding for {target.query}: Product {name} by {mfr}. "
                        f"Targeted attributes: {', '.join(target.target_attributes)}. "
                        f"Information sourced from manufacturer website.",
                source=f"{mfr} Product Page",
                source_url=candidates[0].url,
                source_type=SourceType.MANUFACTURER_WEBSITE,
                score=0.82,
                section="Product Details",
            ))

        evidence_set = EvidenceSet(evidence=evidence_list)
        evidence_set.compute_metrics()

        elapsed = (time.time() - start) * 1000
        return ResearchResult(
            request_id=request.request_id,
            evidence_set=evidence_set,
            source_candidates=candidates,
            sources_evaluated=len(candidates),
            sources_selected=sum(1 for c in candidates if c.selected),
            research_time_ms=elapsed,
        )