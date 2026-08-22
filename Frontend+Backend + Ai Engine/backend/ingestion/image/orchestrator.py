"""Image Intelligence Orchestrator.

Provides the primary public API entrypoint for analyzing industrial product images:
    Image → Preprocessing → OCR + Vision → Evidence JSON → LLM Reasoning → Product Intelligence
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from .config import config
from .evidence_builder import EvidenceBuilder
from .image_processor import ImageProcessingError, ImageProcessor
from .llm_processor import LLMProcessor
from .ocr_engine import OCREngine
from .schemas import (
    ImageAnalysisError,
    ImageAnalysisResponse,
    ProcessingStagesStatus,
    StepStatusEnum,
)
from .vision_analyzer import create_vision_analyzer

logger = logging.getLogger(__name__)


async def analyze_image(
    image_bytes: bytes,
    filename: str = "product.jpg",
    content_type: Optional[str] = None,
    provider: Optional[str] = None,
    image_id: Optional[str] = None,
) -> ImageAnalysisResponse:
    """
    Asynchronously executes the full perception pipeline on an uploaded product image.

    Args:
        image_bytes: Raw bytes of the uploaded image
        filename: Original file name (e.g. 'part_6205.png')
        content_type: Optional MIME type (e.g. 'image/png')
        provider: Optional AI provider override ('gemini' or 'offline')
        image_id: Optional custom identifier

    Returns:
        ImageAnalysisResponse containing metadata, Evidence JSON, and Product Intelligence.
    """
    img_id = image_id or f"img_{uuid.uuid4().hex[:8]}"
    stages = ProcessingStagesStatus()

    # -----------------------------------------------------------------------
    # Step 1: Image Validation & Preprocessing
    # -----------------------------------------------------------------------
    processor = ImageProcessor()
    try:
        processed_bytes, metadata = processor.validate_and_process(
            image_bytes=image_bytes,
            filename=filename,
            content_type=content_type,
        )
        stages.image_preprocessing = StepStatusEnum.COMPLETED
    except ImageProcessingError as e:
        logger.warning(f"Image Intelligence: validation failed ({e.code}) — {e.message}")
        stages.image_preprocessing = StepStatusEnum.FAILED
        return ImageAnalysisResponse(
            success=False,
            image_id=img_id,
            processing=stages,
            error=ImageAnalysisError(
                code=e.code,
                message=e.message,
                stage="image_preprocessing",
            ),
        )
    except Exception as e:
        logger.error(f"Image Intelligence: unexpected preprocessing error — {e}", exc_info=True)
        stages.image_preprocessing = StepStatusEnum.FAILED
        return ImageAnalysisResponse(
            success=False,
            image_id=img_id,
            processing=stages,
            error=ImageAnalysisError(
                code="PREPROCESSING_ERROR",
                message=f"Failed to process image: {str(e)}",
                stage="image_preprocessing",
            ),
        )

    # -----------------------------------------------------------------------
    # Step 2: OCR Text Extraction
    # -----------------------------------------------------------------------
    ocr_engine = OCREngine()
    ocr_output = ocr_engine.extract_text(processed_bytes)
    stages.ocr = ocr_output.status

    # -----------------------------------------------------------------------
    # Step 3: Multimodal Vision Analysis
    # -----------------------------------------------------------------------
    vision_analyzer = create_vision_analyzer(provider=provider)
    mime_type = f"image/{metadata.format.lower()}" if metadata.format else "image/jpeg"
    vision_output = await vision_analyzer.analyze(processed_bytes, mime_type=mime_type)
    stages.vision = vision_output.status

    # -----------------------------------------------------------------------
    # Step 4: Evidence Building
    # -----------------------------------------------------------------------
    evidence_builder = EvidenceBuilder()
    evidence_json = evidence_builder.build_evidence(
        image_metadata=metadata,
        ocr_output=ocr_output,
        vision_output=vision_output,
        image_id=img_id,
    )
    stages.evidence_building = StepStatusEnum.COMPLETED

    # -----------------------------------------------------------------------
    # Step 5: LLM Structuring & Anti-Hallucinatory Reasoning
    # -----------------------------------------------------------------------
    llm_proc = LLMProcessor(provider=provider)
    try:
        product_intelligence = await llm_proc.process_evidence(evidence_json)
        stages.llm_structuring = StepStatusEnum.COMPLETED
    except Exception as e:
        logger.warning(f"Image Intelligence: LLM structuring encountered error — {e}", exc_info=True)
        stages.llm_structuring = StepStatusEnum.FAILED
        product_intelligence = llm_proc._fallback_deterministic_extraction(evidence_json)

    # Sync inferred image_type and component_relationships to evidence if vision was generic or missing them
    if product_intelligence:
        if product_intelligence.image_type and product_intelligence.image_type.value:
            inferred_type = product_intelligence.image_type.value
            if inferred_type != "UNKNOWN" and (evidence_json.image_type == "UNKNOWN" or evidence_json.image_type == "PRODUCT_PHOTOGRAPH"):
                evidence_json.image_type = inferred_type
        if product_intelligence.component_relationships and not evidence_json.component_relationships:
            evidence_json.component_relationships = product_intelligence.component_relationships

    return ImageAnalysisResponse(
        success=True,
        image_id=img_id,
        image_metadata=metadata,
        evidence=evidence_json,
        product_intelligence=product_intelligence,
        processing=stages,
    )
