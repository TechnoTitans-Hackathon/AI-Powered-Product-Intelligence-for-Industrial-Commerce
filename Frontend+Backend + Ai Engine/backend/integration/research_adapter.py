"""Research Adapter — bridges AI engine's ResearchInterface to backend's ExternalKnowledgeProvider.

AI ENGINE decides WHETHER research is needed and WHAT to research.
BACKEND owns the infrastructure for external knowledge acquisition.

This adapter implements the AI engine's abstract ResearchInterface
and delegates actual acquisition to the backend's ExternalKnowledgeProvider.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional, Callable


from ai_engine.research.researcher import ResearchInterface
from ai_engine.schemas import (
    Evidence,
    EvidenceSet,
    ResearchRequest,
    ResearchResult,
    ResearchSourceCandidate,
    SourceType,
)
from backend.knowledge.external_acquisition import external_knowledge_provider
from backend.schemas.retrieval import EvidenceSchema
from backend.core.db import SessionLocal

logger = logging.getLogger(__name__)


def _backend_evidence_to_ai_evidence(ev: EvidenceSchema) -> Evidence:
    """Convert backend EvidenceSchema to AI engine Evidence.

    Preserves all provenance, metadata, content, source information.
    """
    source_type = SourceType.SECONDARY_SOURCE
    if isinstance(ev.provenance, dict):
        st = ev.provenance.get("source_type", "")
        if "manufacturer" in st:
            source_type = SourceType.MANUFACTURER_DOCUMENT
        elif "distributor" in st:
            source_type = SourceType.DISTRIBUTOR_DOCUMENT
        elif "external" in st:
            source_type = SourceType.SECONDARY_SOURCE

    return Evidence(
        evidence_id=ev.evidence_id,
        content=ev.content,
        source=ev.source or "External Research",
        source_type=source_type,
        source_url=ev.url,
        page=ev.page,
        score=ev.score,
        metadata=ev.metadata if isinstance(ev.metadata, dict) else {},
    )


class BackendResearchAdapter(ResearchInterface):
    """Implements the AI engine's ResearchInterface using the backend's
    ExternalKnowledgeProvider.

    The AI engine calls .research(ResearchRequest) when the knowledge
    decision engine determines that evidence is insufficient.

    This adapter:
    1. Creates a DB session (backend's acquisition requires one)
    2. Converts AI engine ResearchRequest -> backend search_and_acquire() calls
    3. Converts backend results -> AI engine ResearchResult
    4. Detects RESEARCH_PROVIDER_UNAVAILABLE and reports it cleanly
    """

    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or SessionLocal

    async def research(self, request: ResearchRequest) -> ResearchResult:
        """Perform targeted external research via the backend's acquisition system."""
        start = time.time()
        logger.info(
            f"BackendResearchAdapter: researching '{request.product_name}' "
            f"(part={request.part_number}, targets={len(request.targets)})"
        )

        all_evidence: list[Evidence] = []
        candidates: list[ResearchSourceCandidate] = []
        research_unavailable = False

        db = self._session_factory()
        try:
            for target in request.targets[:5]:  # Bounded research
                # Build query and missing fields from the research target
                query = target.query
                missing_fields = target.target_attributes

                source_requirements = {
                    "industry": "",
                    "category": "",
                }
                if request.manufacturer:
                    source_requirements["manufacturer"] = request.manufacturer

                # Delegate to backend's external knowledge provider
                backend_results = external_knowledge_provider.search_and_acquire(
                    db=db,
                    query=query,
                    missing_fields=missing_fields,
                    source_requirements=source_requirements,
                )

                for ev in backend_results:
                    # Check for RESEARCH_PROVIDER_UNAVAILABLE
                    if ev.source_id == "RESEARCH_PROVIDER_UNAVAILABLE":
                        research_unavailable = True
                        logger.info(
                            "BackendResearchAdapter: backend reports "
                            "RESEARCH_PROVIDER_UNAVAILABLE"
                        )
                        continue

                    ai_ev = _backend_evidence_to_ai_evidence(ev)
                    all_evidence.append(ai_ev)

                    # Track source candidates
                    candidates.append(ResearchSourceCandidate(
                        url=ev.url or f"backend://evidence/{ev.evidence_id}",
                        title=ev.source or "External Source",
                        source_type=ai_ev.source_type,
                        quality_score=ev.score,
                        selected=True,
                    ))

        except Exception as e:
            logger.error(f"BackendResearchAdapter: research failed — {e}")
            elapsed = (time.time() - start) * 1000
            return ResearchResult(
                request_id=request.request_id,
                evidence_set=EvidenceSet(),
                source_candidates=[],
                sources_evaluated=0,
                sources_selected=0,
                research_time_ms=elapsed,
                error=str(e),
            )
        finally:
            db.close()

        evidence_set = EvidenceSet(evidence=all_evidence)
        if all_evidence:
            evidence_set.compute_metrics()

        elapsed = (time.time() - start) * 1000

        error_msg = None
        if research_unavailable and not all_evidence:
            error_msg = "RESEARCH_PROVIDER_UNAVAILABLE"

        logger.info(
            f"BackendResearchAdapter: completed in {elapsed:.0f}ms. "
            f"Evidence={len(all_evidence)}, Unavailable={research_unavailable}"
        )

        return ResearchResult(
            request_id=request.request_id,
            evidence_set=evidence_set,
            source_candidates=candidates,
            sources_evaluated=len(candidates),
            sources_selected=sum(1 for c in candidates if c.selected),
            research_time_ms=elapsed,
            error=error_msg,
        )
