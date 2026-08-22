"""Discovery agent request/response schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .base import EvidenceSufficiency
from .product import ProductIdentity


class DiscoveryRequest(BaseModel):
    """Input to the Discovery Agent."""
    request_id: str
    mfg_part_number: Optional[str] = None
    part_description: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    extracted_texts: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    additional_context: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRequirement(BaseModel):
    """A single piece of missing knowledge and why it matters."""
    attribute: Any
    importance: Any = "HIGH"  # HIGH, MEDIUM, LOW or int
    reason: Any = ""
    suggested_sources: list[Any] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    """Output from the Discovery Agent."""
    request_id: str
    product_identity: ProductIdentity = Field(default_factory=ProductIdentity)
    industry: Any = None
    category: Any = None
    known_information: Any = Field(default_factory=list)
    missing_information: Any = Field(default_factory=list)
    required_attributes: Any = Field(default_factory=list)
    evidence_requirements: Any = Field(default_factory=list)
    retrieval_queries: Any = Field(default_factory=list)
    external_search_queries: Any = Field(default_factory=list)
    actions: Any = Field(default_factory=list)
    research_required: bool = False
    initial_sufficiency: EvidenceSufficiency = EvidenceSufficiency.INSUFFICIENT
    raw_ai_response: Optional[str] = None


class KnowledgeDecision(BaseModel):
    """Structured decision from the Knowledge Decision Engine."""
    decision: EvidenceSufficiency
    missing_critical_fields: list[Any] = Field(default_factory=list)
    evidence_coverage: float = 0.0
    reason: str = ""
    research_plan: list[dict[str, Any]] = Field(default_factory=list)
    relevant_evidence_summary: Optional[str] = None

