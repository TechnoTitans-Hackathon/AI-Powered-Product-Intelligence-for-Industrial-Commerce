"""Schemas package — all integration contracts."""

from .base import (
    ConflictType,
    EvidenceSufficiency,
    FieldStatus,
    ProcessingError,
    ProcessingStatus,
    ReviewState,
    SourceType,
    SOURCE_AUTHORITY_WEIGHTS,
    TimestampedModel,
)
from .evidence import (
    Conflict,
    Evidence,
    EvidenceSet,
    EvidenceSnippet,
    Provenance,
)
from .product import (
    FieldValue,
    NormalizedInput,
    ProductIdentity,
    ProductInput,
    ProductIntelligenceResult,
)
from .discovery import (
    DiscoveryRequest,
    DiscoveryResult,
    KnowledgeRequirement,
)
from .retrieval import (
    ResearchRequest,
    ResearchResult,
    ResearchSourceCandidate,
    ResearchTarget,
    RetrievalRequest,
    RetrievalResponse,
)
from .confidence_schema import (
    ConfidenceResult,
    ConfidenceSignals,
    ConfidenceWeights,
)
from .validation_schema import (
    ValidationCheck,
    ValidationResult,
)

__all__ = [
    "ConflictType", "EvidenceSufficiency", "FieldStatus", "ProcessingError",
    "ProcessingStatus", "ReviewState", "SourceType", "SOURCE_AUTHORITY_WEIGHTS",
    "TimestampedModel", "Conflict", "Evidence", "EvidenceSet", "EvidenceSnippet",
    "Provenance", "FieldValue", "NormalizedInput", "ProductIdentity",
    "ProductInput", "ProductIntelligenceResult", "DiscoveryRequest",
    "DiscoveryResult", "KnowledgeRequirement", "ResearchRequest",
    "ResearchResult", "ResearchSourceCandidate", "ResearchTarget",
    "RetrievalRequest", "RetrievalResponse", "ConfidenceResult",
    "ConfidenceSignals", "ConfidenceWeights", "ValidationCheck",
    "ValidationResult",
]
