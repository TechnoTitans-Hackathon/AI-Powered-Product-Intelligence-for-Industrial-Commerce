"""Pydantic schemas for the Image Intelligence Module.

Defines strict structures for:
- Preprocessed image metadata
- OCR extracted text and confidence
- Multimodal visual observations
- Combined Evidence JSON
- Field-level evidence and provenance
- Structured Product Intelligence
- API request / response contracts
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FieldStatusEnum(str, Enum):
    """Observation / inference status of a product attribute."""
    OBSERVED = "observed"
    INFERRED = "inferred"
    NOT_OBSERVED = "not_observed"
    UNCERTAIN = "uncertain"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class ImageTypeEnum(str, Enum):
    """Generic industrial image classification type."""
    PRODUCT_PHOTOGRAPH = "PRODUCT_PHOTOGRAPH"
    TECHNICAL_DIAGRAM = "TECHNICAL_DIAGRAM"
    TECHNICAL_DRAWING = "TECHNICAL_DRAWING"
    CUTAWAY_DIAGRAM = "CUTAWAY_DIAGRAM"
    SCHEMATIC = "SCHEMATIC"
    ASSEMBLY_DRAWING = "ASSEMBLY_DRAWING"
    ASSEMBLY_DIAGRAM = "ASSEMBLY_DIAGRAM"
    NAMEPLATE = "NAMEPLATE"
    LABEL = "LABEL"
    LABEL_PHOTO = "LABEL_PHOTO"
    PACKAGING = "PACKAGING"
    EQUIPMENT_PHOTOGRAPH = "EQUIPMENT_PHOTOGRAPH"
    MACHINE_PHOTOGRAPH = "MACHINE_PHOTOGRAPH"
    MACHINE_PHOTO = "MACHINE_PHOTO"
    COMPONENT_PHOTO = "COMPONENT_PHOTO"
    CHART = "CHART"
    GRAPH = "GRAPH"
    DOCUMENT_SCAN = "DOCUMENT_SCAN"
    MIXED = "MIXED"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class EvidenceSourceEnum(str, Enum):
    """Source of the evidence supporting a field."""
    OCR = "OCR"
    VISION = "VISION"
    OCR_VISION = "OCR+VISION"
    VISION_INFERENCE = "VISION_INFERENCE"
    INFERRED = "INFERRED"
    NONE = "NONE"


class QualitativeConfidenceEnum(str, Enum):
    """Qualitative confidence level for UI display without fake precision."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_OBSERVED = "NOT_OBSERVED"


class StepStatusEnum(str, Enum):
    """Status of each perception stage."""
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# Image Metadata
# ---------------------------------------------------------------------------

class ImageMetadata(BaseModel):
    """Metadata extracted during image validation and preprocessing."""
    width: int
    height: int
    format: str
    size_bytes: int
    channels: Optional[str] = None
    color_mode: Optional[str] = None
    aspect_ratio: Optional[float] = None
    resized: bool = False
    original_dimensions: Optional[tuple[int, int]] = None


# ---------------------------------------------------------------------------
# OCR & Component Schemas
# ---------------------------------------------------------------------------

class OCRTextItem(BaseModel):
    """A single recognized text snippet with confidence score and correction tracking."""
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: Optional[List[List[int]]] = None
    normalized_bbox: Optional[List[int]] = None  # [x1, y1, x2, y2] in original image space
    region_type: Optional[str] = "text"
    original_text: Optional[str] = None
    normalized_text: Optional[str] = None
    correction_applied: bool = False
    correction_confidence: float = 0.0
    source: str = "OCR"

    def model_post_init(self, __context: Any) -> None:
        if self.original_text is None:
            self.original_text = self.text
        if self.normalized_text is None:
            self.normalized_text = self.text
        if self.correction_confidence == 0.0:
            self.correction_confidence = self.confidence


class TextRegion(BaseModel):
    """A detected text-bearing region (e.g. nameplate, specification label, packaging mark)."""
    region_id: str
    region_type: str = "text_region"
    bbox: Optional[List[int]] = None  # [x, y, w, h]
    bounding_box: Optional[List[int]] = None  # Alias for bbox
    label: str = "text_region"
    confidence: float = 0.8
    detection_confidence: float = 0.8
    crop_type: Optional[str] = "crop"
    crop_coordinates: Optional[List[int]] = None
    preprocessing_variants_used: List[str] = Field(default_factory=list)
    lines: List[Dict[str, Any]] = Field(default_factory=list)
    raw_text: Optional[str] = None
    unreadable_status: Optional[str] = None
    reason: Optional[str] = None


class ComponentRelationship(BaseModel):
    """Relationship between a text label, leader line/arrow, and physical component."""
    name: str
    type: str = "component"
    label: Optional[str] = None
    source_label: Optional[str] = None
    target_component: Optional[str] = None
    relationship: str = "LABELS"  # "LABELS", "POINTS_TO", "CONTAINS", "supports/located around"
    confidence: float = 0.85
    source: str = "OCR+VISION"
    evidence: Optional[str] = None
    region_id: Optional[str] = None
    bbox: Optional[List[int]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.source_label is None and self.label is not None:
            self.source_label = self.label
        elif self.label is None and self.source_label is not None:
            self.label = self.source_label


class OCROutput(BaseModel):
    """Aggregated OCR engine results."""
    ocr_text: List[OCRTextItem] = Field(default_factory=list)
    low_confidence_ocr: List[OCRTextItem] = Field(default_factory=list)
    unresolved_text: List[str] = Field(default_factory=list)
    ocr_corrections: List[Dict[str, Any]] = Field(default_factory=list)
    text_regions: List[TextRegion] = Field(default_factory=list)
    detected_labels: List[str] = Field(default_factory=list)
    raw_concatenated_text: str = ""
    ocr_details: Optional[Dict[str, Any]] = None
    status: StepStatusEnum = StepStatusEnum.COMPLETED
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Vision Analysis Schemas
# ---------------------------------------------------------------------------

class VisualObservation(BaseModel):
    """Direct visual observation from the multimodal vision model."""
    observation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    location_hint: Optional[str] = None


class EnvironmentObservation(BaseModel):
    """Observed environment or setting in the image."""
    description: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ActivityObservation(BaseModel):
    """Observed activity or use-case in the image."""
    description: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class VisionOutput(BaseModel):
    """Aggregated visual perception results."""
    image_type: str = "UNKNOWN"
    visual_observations: List[VisualObservation] = Field(default_factory=list)
    component_relationships: List[ComponentRelationship] = Field(default_factory=list)
    environment: Optional[EnvironmentObservation] = None
    activities: List[ActivityObservation] = Field(default_factory=list)
    visible_labels: List[str] = Field(default_factory=list)
    status: StepStatusEnum = StepStatusEnum.COMPLETED
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Evidence JSON (The Combined Observation Layer)
# ---------------------------------------------------------------------------

class EvidenceJSON(BaseModel):
    """
    Authoritative Evidence representation.
    Contains ONLY direct observations from OCR, Vision, and Image metadata.
    Does NOT contain unsupported assumptions or hallucinated specifications.
    """
    schema_version: str = "1.0"
    image_id: str
    image_type: str = "UNKNOWN"
    image_metadata: ImageMetadata
    visual_observations: List[VisualObservation] = Field(default_factory=list)
    ocr: List[OCRTextItem] = Field(default_factory=list)
    low_confidence_ocr: List[OCRTextItem] = Field(default_factory=list)
    unresolved_text: List[str] = Field(default_factory=list)
    text_regions: List[TextRegion] = Field(default_factory=list)
    component_relationships: List[ComponentRelationship] = Field(default_factory=list)
    diagram_relationships: List[ComponentRelationship] = Field(default_factory=list)
    environment: Optional[EnvironmentObservation] = None
    activities: List[ActivityObservation] = Field(default_factory=list)
    raw_text: Optional[str] = None
    llm_ready_summary: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.diagram_relationships and self.component_relationships:
            self.diagram_relationships = self.component_relationships
        elif not self.component_relationships and self.diagram_relationships:
            self.component_relationships = self.diagram_relationships


# ---------------------------------------------------------------------------
# Field-Level Evidence & Product Intelligence
# ---------------------------------------------------------------------------

def calculate_qualitative_confidence(confidence: float, status: FieldStatusEnum) -> QualitativeConfidenceEnum:
    """Derives qualitative confidence from numerical score and status."""
    if status == FieldStatusEnum.NOT_OBSERVED or status == FieldStatusEnum.UNSUPPORTED:
        return QualitativeConfidenceEnum.NOT_OBSERVED
    if confidence >= 0.75:
        return QualitativeConfidenceEnum.HIGH
    if confidence >= 0.45:
        return QualitativeConfidenceEnum.MEDIUM
    return QualitativeConfidenceEnum.LOW


class FieldEvidence(BaseModel):
    """
    Single product attribute with full evidence provenance and anti-hallucination tracking.
    """
    field: str
    value: Optional[Any] = None
    source: EvidenceSourceEnum = EvidenceSourceEnum.NONE
    evidence: Optional[str] = None
    confidence: float = 0.0
    status: FieldStatusEnum = FieldStatusEnum.NOT_OBSERVED
    confidence_level: QualitativeConfidenceEnum = QualitativeConfidenceEnum.NOT_OBSERVED
    reason: Optional[str] = None
    region_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """Ensure qualitative confidence aligns with numerical score and status."""
        if self.status in (FieldStatusEnum.NOT_OBSERVED, FieldStatusEnum.UNSUPPORTED) or self.value is None:
            self.confidence_level = QualitativeConfidenceEnum.NOT_OBSERVED
            self.confidence = 0.0
        elif not self.confidence_level or self.confidence_level == QualitativeConfidenceEnum.NOT_OBSERVED:
            self.confidence_level = calculate_qualitative_confidence(self.confidence, self.status)


class ProductIntelligenceOutput(BaseModel):
    """
    Structured Product Intelligence produced by LLM reasoning over Evidence JSON.
    Guarantees that unobserved fields are explicitly marked 'not_observed'.
    """
    image_type: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="image_type", value="UNKNOWN", status=FieldStatusEnum.OBSERVED, confidence=0.9))
    product_name: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="product_name"))
    product_type: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="product_type"))
    category: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="category"))
    subcategory: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="subcategory"))
    brand: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="brand"))
    model: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="model"))
    sku: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="sku"))
    dimensions: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="dimensions"))
    weight: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="weight"))
    material: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="material"))
    voltage: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="voltage"))
    current: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="current"))
    power: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="power"))
    frequency: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="frequency"))
    pressure: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="pressure"))
    flow: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="flow"))
    color: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="color"))
    description: FieldEvidence = Field(default_factory=lambda: FieldEvidence(field="description"))
    
    # Collections / Dynamic Lists
    components: List[FieldEvidence] = Field(default_factory=list)
    component_relationships: List[ComponentRelationship] = Field(default_factory=list)
    diagram_relationships: List[ComponentRelationship] = Field(default_factory=list)
    applications: List[FieldEvidence] = Field(default_factory=list)
    features: List[FieldEvidence] = Field(default_factory=list)
    certifications: List[FieldEvidence] = Field(default_factory=list)
    visible_labels: List[FieldEvidence] = Field(default_factory=list)
    additional_attributes: List[FieldEvidence] = Field(default_factory=list)
    llm_ready_summary: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.diagram_relationships and self.component_relationships:
            self.diagram_relationships = self.component_relationships
        elif not self.component_relationships and self.diagram_relationships:
            self.component_relationships = self.diagram_relationships

    # Statistical Summary
    observed_fields_count: int = 0
    inferred_fields_count: int = 0
    not_observed_fields_count: int = 0


# ---------------------------------------------------------------------------
# API Contracts & Processing Results
# ---------------------------------------------------------------------------

class ProcessingStagesStatus(BaseModel):
    """Status tracker for perception stages."""
    image_preprocessing: StepStatusEnum = StepStatusEnum.COMPLETED
    ocr: StepStatusEnum = StepStatusEnum.COMPLETED
    vision: StepStatusEnum = StepStatusEnum.COMPLETED
    evidence_building: StepStatusEnum = StepStatusEnum.COMPLETED
    llm_structuring: StepStatusEnum = StepStatusEnum.COMPLETED


class ImageAnalysisError(BaseModel):
    """Standardized error structure."""
    code: str
    message: str
    stage: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ImageAnalysisResponse(BaseModel):
    """Complete API response for image analysis endpoint."""
    schema_version: str = "1.0"
    success: bool
    image_id: Optional[str] = None
    image_metadata: Optional[ImageMetadata] = None
    evidence: Optional[EvidenceJSON] = None
    product_intelligence: Optional[ProductIntelligenceOutput] = None
    processing: ProcessingStagesStatus = Field(default_factory=ProcessingStagesStatus)
    error: Optional[ImageAnalysisError] = None
