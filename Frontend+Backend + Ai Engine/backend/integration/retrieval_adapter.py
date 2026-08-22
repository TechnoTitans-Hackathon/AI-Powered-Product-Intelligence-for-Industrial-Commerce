"""Retrieval Adapter — bridges AI engine's RetrieverInterface to backend's RetrievalService.

AI ENGINE owns the intelligence decision of WHAT to retrieve.
BACKEND owns the infrastructure of HOW to retrieve it.

This adapter implements the AI engine's abstract RetrieverInterface
and delegates actual retrieval to the backend's vector store via RetrievalService.
"""

from __future__ import annotations

import logging
import time
from typing import Optional


from ai_engine.retrieval.retriever import RetrieverInterface
from ai_engine.schemas import (
    Evidence,
    EvidenceSet,
    RetrievalRequest,
    RetrievalResponse,
    SourceType,
)
from backend.retrieval.retrieval_service import retrieval_service
from backend.schemas.retrieval import EvidenceSchema, RetrievalFilter

logger = logging.getLogger(__name__)

# Map backend source_type strings to AI engine SourceType enum
_SOURCE_TYPE_MAP = {
    "manufacturer_document": SourceType.MANUFACTURER_DOCUMENT,
    "manufacturer_website": SourceType.MANUFACTURER_WEBSITE,
    "distributor_document": SourceType.DISTRIBUTOR_DOCUMENT,
    "distributor_website": SourceType.DISTRIBUTOR_DOCUMENT,
    "external_on_demand": SourceType.SECONDARY_SOURCE,
    "document": SourceType.SECONDARY_SOURCE,
    "user_upload": SourceType.SECONDARY_SOURCE,
    "baseline": SourceType.MANUFACTURER_DOCUMENT,
}


def _backend_evidence_to_ai_evidence(ev: EvidenceSchema) -> Evidence:
    """Convert a backend EvidenceSchema to the AI engine's Evidence model.

    Preserves: content, source, url, score, page, metadata, provenance.
    Never discards provenance information.
    """
    source_type_str = (
        ev.provenance.get("source_type", "")
        if isinstance(ev.provenance, dict)
        else "document"
    )
    source_type = _SOURCE_TYPE_MAP.get(source_type_str, SourceType.SECONDARY_SOURCE)

    return Evidence(
        evidence_id=ev.evidence_id,
        content=ev.content,
        source=ev.source or "Unknown Source",
        source_type=source_type,
        source_url=ev.url,
        page=ev.page,
        section=ev.metadata.get("section") if isinstance(ev.metadata, dict) else None,
        score=ev.score,
        metadata=ev.metadata if isinstance(ev.metadata, dict) else {},
    )


class BackendRetrieverAdapter(RetrieverInterface):
    """Implements the AI engine's RetrieverInterface using the backend's
    RetrievalService (vector store).

    The AI engine calls .retrieve(RetrievalRequest) when it needs evidence.
    This adapter translates the request to the backend's search API and
    converts the results back to the AI engine's Evidence format.
    """

    def __init__(self, service=None):
        self._service = service or retrieval_service

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Retrieve evidence from the backend's vector store."""
        start = time.time()
        logger.info(f"BackendRetrieverAdapter: query='{request.query[:80]}'")

        try:
            # Build backend filters from AI engine request
            filters = None
            if request.filters:
                filters = RetrievalFilter(
                    category=request.filters.get("category"),
                    source_id=request.filters.get("source_id"),
                )

            # Delegate to backend retrieval service
            backend_results = self._service.search(
                query=request.query,
                top_k=min(request.max_results, 20),
                filters=filters,
            )

            # Convert backend EvidenceSchema[] -> AI engine Evidence[]
            ai_evidence = []
            for ev in backend_results:
                # Skip RESEARCH_PROVIDER_UNAVAILABLE markers
                if ev.source_id == "RESEARCH_PROVIDER_UNAVAILABLE":
                    continue
                # Apply minimum score filter
                if ev.score >= request.min_score:
                    ai_evidence.append(_backend_evidence_to_ai_evidence(ev))

            evidence_set = EvidenceSet(evidence=ai_evidence)
            evidence_set.compute_metrics()

            elapsed = (time.time() - start) * 1000
            logger.info(
                f"BackendRetrieverAdapter: returned {len(ai_evidence)} evidence "
                f"items in {elapsed:.0f}ms"
            )

            return RetrievalResponse(
                evidence_set=evidence_set,
                query_used=request.query,
                retrieval_time_ms=elapsed,
                source_count=len(ai_evidence),
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"BackendRetrieverAdapter: retrieval failed — {e}")
            return RetrievalResponse(
                evidence_set=EvidenceSet(),
                query_used=request.query,
                retrieval_time_ms=elapsed,
                source_count=0,
                error=str(e),
            )
