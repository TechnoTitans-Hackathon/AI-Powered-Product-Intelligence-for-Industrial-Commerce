import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.schemas.retrieval import EvidenceSchema
from backend.knowledge.storage import storage_manager
from backend.knowledge.cache_manager import cache_manager
from backend.ingestion.url_processor import URLProcessor
from backend.core.storage_safety import storage_safety
from backend.core.logging import logger

class ExternalKnowledgeProvider(ABC):
    """
    Abstract interface for on-demand external knowledge acquisition.
    Used when local evidence retrieval is insufficient for an input query.
    """

    @abstractmethod
    def search_and_acquire(
        self,
        db: Session,
        query: str,
        missing_fields: List[str],
        source_requirements: Optional[Dict[str, Any]] = None
    ) -> List[EvidenceSchema]:
        pass

class StandardExternalKnowledgeProvider(ExternalKnowledgeProvider):
    """
    Default implementation of targeted external acquisition:
    1. Evaluates missing information requirement & query.
    2. Checks for duplicate content before downloading.
    3. Checks available storage budget before acquisition.
    4. Fetches authoritative source content (simulated / HTTP fetch).
    5. Validates source integrity and stores content in temporary cache.
    6. Ingests content using URLProcessor and extracts structured evidence.
    7. Returns evidence with complete traceable provenance.

    RULES:
    - NEVER fabricates product-specific data (no SKF, no bearing specs, no 6205).
    - Content reflects the ACTUAL query terms and context.
    - All simulated content is marked as [simulated_acquisition].
    """

    def search_and_acquire(
        self,
        db: Session,
        query: str,
        missing_fields: List[str],
        source_requirements: Optional[Dict[str, Any]] = None
    ) -> List[EvidenceSchema]:
        requirements = source_requirements or {}
        industry = requirements.get("industry", "")
        category = requirements.get("category", "")

        logger.info(
            f"Targeted External Knowledge Acquisition triggered for query: '{query}', "
            f"industry: '{industry}', category: '{category}', "
            f"missing fields: {missing_fields}"
        )

        # As per Phase 15 & 16: External acquisition must be real or explicitly unavailable.
        # Currently, no real search provider/API is configured.
        # We must return RESEARCH_PROVIDER_UNAVAILABLE and NOT fake any evidence.
        logger.info(f"Targeted acquisition requested, but no real research provider is configured. Returning unavailable.")
        
        # We return a structured failure/unavailable state as evidence for tracking
        unavailable_evidence = EvidenceSchema(
            evidence_id=f"ev_ext_{uuid.uuid4().hex[:8]}",
            source_id="RESEARCH_PROVIDER_UNAVAILABLE",
            source="External Targeted Acquisition",
            document="",
            url="",
            page=1,
            content="RESEARCH_PROVIDER_UNAVAILABLE",
            score=0.0,
            metadata={
                "query": query,
                "missing_fields": missing_fields,
                "industry": industry,
                "category": category,
                "acquisition_type": "TEMPORARY_ACQUISITION",
                "status": "RESEARCH_PROVIDER_UNAVAILABLE"
            },
            provenance={
                "source_type": "external_on_demand",
                "status": "RESEARCH_PROVIDER_UNAVAILABLE",
                "industry": industry,
                "category": category
            }
        )
        return [unavailable_evidence]

external_knowledge_provider = StandardExternalKnowledgeProvider()
