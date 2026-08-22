"""Retrieval and research interface schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import SourceType
from .discovery import DiscoveryResult
from .evidence import EvidenceSet


# ---------------------------------------------------------------------------
# Retrieval contract
# ---------------------------------------------------------------------------

class RetrievalRequest(BaseModel):
    """Request to the retrieval system (RAG / vector DB)."""
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    product_context: dict[str, Any] = Field(default_factory=dict)
    required_attributes: list[str] = Field(default_factory=list)
    max_results: int = 10
    min_score: float = 0.5


class RetrievalResponse(BaseModel):
    """Response from the retrieval system."""
    evidence_set: EvidenceSet = Field(default_factory=EvidenceSet)
    query_used: str = ""
    retrieval_time_ms: float = 0.0
    source_count: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Research (external knowledge acquisition) contract
# ---------------------------------------------------------------------------

class ResearchTarget(BaseModel):
    """A specific research target."""
    query: str
    target_attributes: list[Any] = Field(default_factory=list)
    preferred_source_types: list[SourceType] = Field(default_factory=list)
    priority: Any = "MEDIUM"  # HIGH, MEDIUM, LOW


class ResearchRequest(BaseModel):
    """Request for external knowledge acquisition."""
    request_id: str
    product_name: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    targets: list[ResearchTarget] = Field(default_factory=list)
    max_sources: int = 5
    timeout_seconds: int = 30


class ResearchSourceCandidate(BaseModel):
    """A candidate source found during research."""
    url: str
    title: Optional[str] = None
    source_type: SourceType = SourceType.UNKNOWN_SOURCE
    quality_score: float = 0.0
    selected: bool = False
    rejection_reason: Optional[str] = None


class ResearchResult(BaseModel):
    """Result from external research."""
    request_id: str
    evidence_set: EvidenceSet = Field(default_factory=EvidenceSet)
    source_candidates: list[ResearchSourceCandidate] = Field(default_factory=list)
    sources_evaluated: int = 0
    sources_selected: int = 0
    research_time_ms: float = 0.0
    error: Optional[str] = None
    partial: bool = False
