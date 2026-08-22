from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    VISUAL = "visual"
    OCR = "ocr"


class EvidenceRecord(BaseModel):
    evidence_id: str
    type: EvidenceType
    timestamp_start: Optional[float] = 0.0
    timestamp_end: Optional[float] = 0.0
    frame_id: Optional[str] = None
    content: str
    confidence: float = 1.0
    source: str = "pdf"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentClassification(str, Enum):
    TEXT = "TEXT"
    SCANNED = "SCANNED"
    MIXED = "MIXED"
    IMAGE_HEAVY = "IMAGE_HEAVY"
    TECHNICAL_DOCUMENT = "TECHNICAL_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class ChunkContentType(str, Enum):
    TEXT = "TEXT"
    TABLE = "TABLE"
    IMAGE = "IMAGE"
    OCR = "OCR"
    CAPTION = "CAPTION"
    DIAGRAM = "DIAGRAM"
    LIST = "LIST"
    HEADER = "HEADER"
    FOOTNOTE = "FOOTNOTE"


class AttributeStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class ImageClassification(str, Enum):
    PHOTOGRAPH = "photograph"
    PRODUCT_PHOTOGRAPH = "product_photograph"
    TECHNICAL_DRAWING = "technical_drawing"
    SCHEMATIC = "schematic"
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    CHART = "chart"
    GRAPH = "graph"
    TABLE_IMAGE = "table_image"
    SCREENSHOT = "screenshot"
    SCANNED_DOCUMENT = "scanned_document"
    LOGO = "logo"
    MAP = "map"
    MIXED = "mixed"
    ILLUSTRATION = "illustration"
    UNKNOWN_IMAGE = "unknown_image"


class PDFMetadata(BaseModel):
    document_id: str
    filename: str
    file_hash: str
    file_size_bytes: int
    page_count: int
    upload_timestamp: str
    storage_path: str
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    producer: Optional[str] = None


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class TextBlock(BaseModel):
    block_id: str
    page_number: int
    text: str
    block_type: str = "paragraph"
    section: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    reading_order_idx: int = 0


class PDFTableCell(BaseModel):
    row_idx: int
    col_idx: int
    column_name: str
    value: str
    unit: Optional[str] = None
    is_header: bool = False
    row_header: Optional[str] = None


class PDFTable(BaseModel):
    table_id: str
    page_number: int
    title: Optional[str] = None
    section: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_headers: Optional[List[str]] = None
    units: Dict[str, str] = Field(default_factory=dict)
    merged_cells: Optional[List[Dict[str, Any]]] = None
    footnotes: Optional[List[str]] = None
    bbox: Optional[BoundingBox] = None
    text_representation: str


class PDFOCRBlock(BaseModel):
    ocr_id: str
    page_number: int
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    is_uncertain: bool = False
    bbox: Optional[BoundingBox] = None
    strategy_used: str = "original"
    source_region: Optional[str] = None


class ImageObservation(BaseModel):
    observation_id: str
    image_id: str
    page_number: int
    observation_type: str
    value: str
    source_type: str = "visual"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bbox: Optional[BoundingBox] = None
    evidence_text: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


class PDFImageNode(BaseModel):
    image_id: str
    page_number: int
    classification: ImageClassification = ImageClassification.UNKNOWN_IMAGE
    caption: Optional[str] = None
    section: Optional[str] = None
    storage_path: str
    bbox: Optional[BoundingBox] = None
    width: int = 0
    height: int = 0
    format: str = "png"
    vision_observations: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_blocks: List[PDFOCRBlock] = Field(default_factory=list)
    quality_assessment: Dict[str, Any] = Field(default_factory=dict)
    visual_summary: Optional[str] = None
    image_evidence: List[ImageObservation] = Field(default_factory=list)


class PDFDocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    section: Optional[str] = None
    content_type: ChunkContentType
    text: str
    source: str
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PDFPageNode(BaseModel):
    page_number: int
    width: float
    height: float
    text_density: float = 0.0
    is_scanned: bool = False
    text_blocks: List[TextBlock] = Field(default_factory=list)
    tables: List[PDFTable] = Field(default_factory=list)
    images: List[PDFImageNode] = Field(default_factory=list)
    ocr_blocks: List[PDFOCRBlock] = Field(default_factory=list)


class AttributeEvidence(BaseModel):
    attribute_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    status: AttributeStatus = AttributeStatus.OBSERVED
    page_number: int
    source_type: str
    confidence: float = 1.0
    raw_snippet: str


class ConflictRecord(BaseModel):
    conflict_id: str
    attribute_or_topic: str
    variations: List[Dict[str, Any]]
    message: str


class PDFAnalysisResult(BaseModel):
    document_id: str
    filename: str
    classification: DocumentClassification
    summary: str
    llm_text: str
    metadata: PDFMetadata
    pages: List[PDFPageNode] = Field(default_factory=list)
    tables: List[PDFTable] = Field(default_factory=list)
    images: List[PDFImageNode] = Field(default_factory=list)
    ocr_content: List[PDFOCRBlock] = Field(default_factory=list)
    chunks: List[PDFDocumentChunk] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    observed_attributes: List[AttributeEvidence] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    processing_time_seconds: float = 0.0


class DocumentEvidenceBundle(BaseModel):
    document_id: str
    filename: str
    document_type: str = "pdf"
    classification: DocumentClassification
    summary: str
    relevant_content: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[PDFTable] = Field(default_factory=list)
    ocr_content: List[PDFOCRBlock] = Field(default_factory=list)
    visual_evidence: List[PDFImageNode] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PDFQueryRequest(BaseModel):
    query: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    content_types: Optional[List[ChunkContentType]] = None
    limit: int = 10


class PDFQueryResponse(BaseModel):
    document_id: str
    query: str
    relevant_chunks: List[PDFDocumentChunk] = Field(default_factory=list)
    evidence_bundle: DocumentEvidenceBundle
