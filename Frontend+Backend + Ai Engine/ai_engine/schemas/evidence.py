"""Evidence, provenance, and conflict schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import ConflictType, SourceType, TimestampedModel, EvidenceClass


class EvidenceSnippet(BaseModel):
    """A single piece of supporting evidence."""
    source: str
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: str
    source_url: Optional[str] = None
    source_type: SourceType = SourceType.UNKNOWN_SOURCE
    score: float = 0.0
    evidence_class: EvidenceClass = EvidenceClass.PROVISIONAL
    trust_score: float = 0.0


class Evidence(BaseModel):
    """A fully qualified evidence record with provenance."""
    evidence_id: str
    content: str
    source: str
    source_url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    timestamp: Optional[str] = None
    score: float = 0.0
    source_type: SourceType = SourceType.UNKNOWN_SOURCE
    dataset_id: Optional[str] = None
    evidence_class: EvidenceClass = EvidenceClass.PROVISIONAL
    trust_score: float = 0.0
    license_status: Optional[str] = None
    retrieval_timestamp: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSet(BaseModel):
    """Collection of evidence with quality metrics."""
    evidence: list[Evidence] = Field(default_factory=list)
    total_sources: int = 0
    average_score: float = 0.0
    source_types_present: list[SourceType] = Field(default_factory=list)
    has_manufacturer_source: bool = False
    coverage_ratio: float = 0.0  # proportion of required attributes covered

    def compute_metrics(self) -> None:
        """Recompute aggregate metrics from evidence list."""
        self.total_sources = len(self.evidence)
        if self.evidence:
            self.average_score = sum(e.score for e in self.evidence) / len(self.evidence)
            types = list({e.source_type for e in self.evidence})
            self.source_types_present = types
            self.has_manufacturer_source = any(
                e.source_type in (SourceType.MANUFACTURER_DOCUMENT, SourceType.MANUFACTURER_WEBSITE)
                for e in self.evidence
            )


class Conflict(BaseModel):
    """Represents a conflict between two evidence sources."""
    field_name: str
    value_a: str
    source_a: str
    source_a_type: SourceType = SourceType.UNKNOWN_SOURCE
    value_b: str
    source_b: str
    source_b_type: SourceType = SourceType.UNKNOWN_SOURCE
    conflict_type: ConflictType = ConflictType.VALUE_MISMATCH
    resolution: Optional[str] = None
    resolved_value: Optional[str] = None
    confidence: float = 0.0
    review_required: bool = True
    reasoning: Optional[str] = None


class Provenance(TimestampedModel):
    """Tracks the origin and lifecycle of a generated value."""
    source_agent: str  # which agent produced this
    model_version: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    generation_version: int = 1
    previous_value: Optional[str] = None
    change_reason: Optional[str] = None
    evidence_class: Optional[EvidenceClass] = None
