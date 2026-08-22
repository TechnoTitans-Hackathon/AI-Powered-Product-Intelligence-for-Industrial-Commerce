"""Base enums and shared types for the AI Product Intelligence Engine."""

from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FieldStatus(str, Enum):
    """Status of a single generated field value."""
    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
    INFERRED = "INFERRED"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class ReviewState(str, Enum):
    """Human-review lifecycle states."""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    NOT_REVIEWED = "NOT_REVIEWED"


class SourceType(str, Enum):
    """Source authority hierarchy (order = priority)."""
    MANUFACTURER_DOCUMENT = "MANUFACTURER_DOCUMENT"
    MANUFACTURER_WEBSITE = "MANUFACTURER_WEBSITE"
    CERTIFICATION_DOCUMENT = "CERTIFICATION_DOCUMENT"
    AUTHORIZED_CATALOG = "AUTHORIZED_CATALOG"
    INDUSTRY_SOURCE = "INDUSTRY_SOURCE"
    DISTRIBUTOR_DOCUMENT = "DISTRIBUTOR_DOCUMENT"
    SECONDARY_SOURCE = "SECONDARY_SOURCE"
    AI_INFERENCE = "AI_INFERENCE"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"


# Source authority weights (higher = more authoritative)
SOURCE_AUTHORITY_WEIGHTS: dict[SourceType, float] = {
    SourceType.MANUFACTURER_DOCUMENT: 1.0,
    SourceType.MANUFACTURER_WEBSITE: 0.95,
    SourceType.CERTIFICATION_DOCUMENT: 0.93,
    SourceType.AUTHORIZED_CATALOG: 0.85,
    SourceType.INDUSTRY_SOURCE: 0.75,
    SourceType.DISTRIBUTOR_DOCUMENT: 0.70,
    SourceType.SECONDARY_SOURCE: 0.50,
    SourceType.AI_INFERENCE: 0.30,
    SourceType.UNKNOWN_SOURCE: 0.20,
}


class EvidenceSufficiency(str, Enum):
    """Result of the knowledge decision engine."""
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    IDENTITY_UNCERTAIN = "IDENTITY_UNCERTAIN"
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED"


class ProcessingStatus(str, Enum):
    """Overall processing state for a product."""
    QUEUED = "QUEUED"
    DISCOVERING = "DISCOVERING"
    RETRIEVING = "RETRIEVING"
    RESEARCHING = "RESEARCHING"
    ENRICHING = "ENRICHING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ConflictType(str, Enum):
    """Types of evidence conflict."""
    VALUE_MISMATCH = "VALUE_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    SOURCE_DISAGREEMENT = "SOURCE_DISAGREEMENT"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    PRECISION_DIFFERENCE = "PRECISION_DIFFERENCE"


class EvidenceClass(str, Enum):
    """Tier of knowledge for permanent evidence."""
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"


# ---------------------------------------------------------------------------
# Shared base models
# ---------------------------------------------------------------------------

class TimestampedModel(BaseModel):
    """Base model with audit timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingError(BaseModel):
    """Structured error representation."""
    stage: str
    error_type: str
    message: str
    recoverable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
