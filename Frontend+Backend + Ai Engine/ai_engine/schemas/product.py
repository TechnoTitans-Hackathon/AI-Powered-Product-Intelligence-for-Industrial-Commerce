"""Product input, field-value, and intelligence result schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .base import (
    FieldStatus,
    ProcessingStatus,
    ReviewState,
    TimestampedModel,
)
from .evidence import Conflict, EvidenceSnippet, Provenance


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class ProductInput(BaseModel):
    """Raw product input as provided by the user / upstream system."""
    product_id: Optional[str] = None
    mfg_part_number: Optional[str] = None
    part_description: Optional[str] = None
    brand: Optional[str] = None
    unilog_brand: Optional[str] = None
    dib_brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    urls: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    additional_text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "product_id", "mfg_part_number", "brand", "unilog_brand",
        "dib_brand", "manufacturer", "category", "industry", mode="before"
    )
    @classmethod
    def normalize_string_identifiers(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, float):
            if v.is_integer():
                return str(int(v))
        if isinstance(v, str) and v.endswith(".0") and v[:-2].isdigit():
            return v[:-2]
        return str(v)


class NormalizedInput(BaseModel):
    """Processed multimodal input — the contract between ingestion and AI."""
    product_input: ProductInput
    
    # Text derived
    text: Optional[str] = None
    pdf_content: Optional[str] = None
    doc_content: Optional[str] = None
    txt_content: Optional[str] = None
    
    # Visual derived
    images: list[dict[str, Any]] = Field(default_factory=list)
    ocr_results: list[str] = Field(default_factory=list)
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    
    # Structured derived
    tables: list[dict[str, Any]] = Field(default_factory=list)
    csv_data: list[dict[str, Any]] = Field(default_factory=list)
    excel_data: list[dict[str, Any]] = Field(default_factory=list)
    
    # Video derived
    video_transcripts: list[dict[str, Any]] = Field(default_factory=list)
    video_timestamps: list[dict[str, Any]] = Field(default_factory=list)
    video_keyframes: list[dict[str, Any]] = Field(default_factory=list)
    
    # Web derived
    urls_content: list[dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    source_metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Field-level intelligence
# ---------------------------------------------------------------------------

class FieldValue(BaseModel):
    """A single enriched field with full traceability."""
    field_name: str
    value: Optional[str] = None
    normalized_value: Optional[Any] = None
    unit: Optional[str] = None
    display_value: Optional[str] = None
    status: FieldStatus = FieldStatus.MISSING
    confidence: float = 0.0
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    reason: Optional[str] = None
    validation_passed: Optional[bool] = None
    review_state: ReviewState = ReviewState.NOT_REVIEWED
    provenance: Optional[Provenance] = None
    conflicts: list[Conflict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Product identity
# ---------------------------------------------------------------------------

class ProductIdentity(BaseModel):
    """Identified product metadata."""
    manufacturer: Any = None
    manufacturer_name_clean: Any = None
    brand: Any = None
    trade_name: Any = None
    part_number: Any = None
    alternate_part_number: Any = None
    product_name: Any = None
    category: Any = None
    department: Any = None
    product_class: Any = None
    fine_class: Any = None
    industry: Any = None
    classpath: Any = None
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Full intelligence result
# ---------------------------------------------------------------------------

class ProductIntelligenceResult(TimestampedModel):
    """Complete product intelligence output from the AI brain."""
    request_id: str
    product_input: ProductInput
    processing_status: ProcessingStatus = ProcessingStatus.QUEUED

    # Identity
    identity: ProductIdentity = Field(default_factory=ProductIdentity)

    # Descriptions
    short_description: Optional[FieldValue] = None
    long_description: Optional[FieldValue] = None
    marketing_description: Optional[FieldValue] = None
    retail_description: Optional[FieldValue] = None
    mobile_description: Optional[FieldValue] = None
    invoice_description: Optional[FieldValue] = None

    # Features (up to 20)
    features: list[FieldValue] = Field(default_factory=list)

    # Applications, standards, includes
    applications: Optional[FieldValue] = None
    standards_approvals: Optional[FieldValue] = None
    includes: Optional[FieldValue] = None
    with_info: Optional[FieldValue] = None
    prop_65: Optional[FieldValue] = None

    # Attributes (label/value/uom triplets)
    attributes: list[FieldValue] = Field(default_factory=list)

    # Physical dimensions
    dimensions: dict[str, FieldValue] = Field(default_factory=dict)

    # Identifiers
    upc: Optional[FieldValue] = None
    ean: Optional[FieldValue] = None
    gtin: Optional[FieldValue] = None
    unspsc: Optional[FieldValue] = None

    # Commercial
    warranty: Optional[FieldValue] = None
    list_price: Optional[FieldValue] = None
    selling_qty: Optional[FieldValue] = None
    selling_uom: Optional[FieldValue] = None
    country_of_origin: Optional[FieldValue] = None
    discontinued: Optional[FieldValue] = None

    # Media
    images: list[FieldValue] = Field(default_factory=list)
    documents: list[FieldValue] = Field(default_factory=list)
    video_links: list[FieldValue] = Field(default_factory=list)

    # URLs / references
    mfr_url: Optional[FieldValue] = None
    reference_urls: list[FieldValue] = Field(default_factory=list)

    # Overall metrics
    overall_confidence: float = 0.0
    fields_total: int = 0
    fields_populated: int = 0
    fields_missing: int = 0
    fields_conflicting: int = 0
    fields_needing_review: int = 0
    completeness_ratio: float = 0.0

    # Conflicts
    conflicts: list[Conflict] = Field(default_factory=list)

    # Errors
    errors: list[dict[str, Any]] = Field(default_factory=list)

    # Enrichment version
    enrichment_version: int = 1
    previous_result_id: Optional[str] = None
