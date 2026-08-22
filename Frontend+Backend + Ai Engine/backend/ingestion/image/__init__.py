"""Image Intelligence Module for Industrial Commerce.

Provides isolated multimodal perception and evidence extraction:
    Image → Preprocessing → OCR + Vision → Evidence JSON → LLM Reasoning → Product Intelligence
"""

from .config import config
from .evidence_builder import EvidenceBuilder
from .image_processor import ImageProcessingError, ImageProcessor
from .llm_processor import LLMProcessor
from .ocr_engine import OCREngine
from .orchestrator import analyze_image
from .schemas import (
    EvidenceJSON,
    EvidenceSourceEnum,
    FieldEvidence,
    FieldStatusEnum,
    ImageAnalysisError,
    ImageAnalysisResponse,
    ImageMetadata,
    OCROutput,
    OCRTextItem,
    ProcessingStagesStatus,
    ProductIntelligenceOutput,
    QualitativeConfidenceEnum,
    StepStatusEnum,
    VisionOutput,
    VisualObservation,
)
from .vision_analyzer import (
    GeminiVisionAnalyzer,
    VisionAnalyzerInterface,
    create_vision_analyzer,
)

__all__ = [
    "analyze_image",
    "config",
    "ImageProcessor",
    "ImageProcessingError",
    "OCREngine",
    "VisionAnalyzerInterface",
    "GeminiVisionAnalyzer",
    "create_vision_analyzer",
    "EvidenceBuilder",
    "LLMProcessor",
    "ImageMetadata",
    "OCRTextItem",
    "OCROutput",
    "VisualObservation",
    "VisionOutput",
    "EvidenceJSON",
    "FieldStatusEnum",
    "EvidenceSourceEnum",
    "QualitativeConfidenceEnum",
    "FieldEvidence",
    "ProductIntelligenceOutput",
    "ProcessingStagesStatus",
    "ImageAnalysisError",
    "ImageAnalysisResponse",
    "StepStatusEnum",
]
