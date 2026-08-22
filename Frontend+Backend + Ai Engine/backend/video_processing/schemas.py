from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class EvidenceType(str, Enum):
    VISUAL = "visual"
    OCR = "ocr"
    SPEECH = "speech"
    SCENE = "scene"
    ACTION = "action"
    METADATA = "metadata"


class AnalysisIntent(str, Enum):
    SUMMARY = "summary"
    TIMELINE = "timeline"
    OCR_FOCUS = "ocr_focus"
    VISUAL_PRODUCT = "visual_product"
    SPEECH_FOCUS = "speech_focus"
    SPECIFICATIONS = "specifications"
    MULTIMODAL = "multimodal"


class FactStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING = "CONFLICTING"


class VideoMetadata(BaseModel):
    video_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    fps: float
    frame_count: int
    has_audio: bool
    has_video_stream: bool
    created_at: str


class SelectedFrame(BaseModel):
    frame_id: str
    timestamp: float
    frame_index: int
    file_reference: str
    reason_selected: str  # scene_change, periodic, ocr_candidate, uniform_sample


class VisionObservation(BaseModel):
    frame_id: str
    timestamp: float
    observation_type: str  # object, scene, action, technical_info
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: Optional[List[float]] = None
    details: Optional[Dict[str, Any]] = None


class OCRResult(BaseModel):
    ocr_id: str
    frame_id: str
    timestamp: float
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: Optional[List[float]] = None  # [x, y, w, h] normalized or absolute


class TranscriptSegment(BaseModel):
    segment_id: str
    start: float
    end: float
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    speaker: Optional[str] = None


class EvidenceRecord(BaseModel):
    evidence_id: str
    type: EvidenceType
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    frame_id: Optional[str] = None
    content: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str  # vision, ocr, speech, metadata, temporal
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    event_id: str
    start: float
    end: float
    event: str
    category: Optional[str] = "general"
    evidence_ids: List[str] = Field(default_factory=list)


class FactRecord(BaseModel):
    fact_id: str
    claim: str
    value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    status: FactStatus = FactStatus.VERIFIED
    reason: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class ConfidenceBreakdown(BaseModel):
    overall_confidence: float = Field(ge=0.0, le=1.0)
    ocr_confidence: Optional[float] = None
    stt_confidence: Optional[float] = None
    vision_confidence: Optional[float] = None
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    temporal_consistency: float = Field(ge=0.0, le=1.0)


class ProcessingStats(BaseModel):
    frames_analyzed: int
    audio_processed: bool
    ocr_processed: bool
    duration_seconds: float
    processing_time_seconds: float


class VideoAnalysisResponse(BaseModel):
    video_id: str
    analysis_id: str
    query: str
    intent: AnalysisIntent
    summary: str
    facts: List[FactRecord] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    confidence: ConfidenceBreakdown
    limitations: List[str] = Field(default_factory=list)
    processing: ProcessingStats
    metadata: VideoMetadata
    status: ProcessingStatus = ProcessingStatus.COMPLETED


class VideoAnalysisRequest(BaseModel):
    video_path: Optional[str] = None
    video_id: Optional[str] = None
    query: Optional[str] = "Provide a comprehensive structured analysis of this video."
    intent: Optional[AnalysisIntent] = None
    time_start: Optional[float] = None
    time_end: Optional[float] = None


class EvidenceQueryRequest(BaseModel):
    query: str
    time_start: Optional[float] = None
    time_end: Optional[float] = None
    types: Optional[List[EvidenceType]] = None
    limit: int = 20


class VideoJobStatusResponse(BaseModel):
    analysis_id: str
    video_id: str
    status: ProcessingStatus
    progress_percentage: float
    message: str
    result: Optional[VideoAnalysisResponse] = None
