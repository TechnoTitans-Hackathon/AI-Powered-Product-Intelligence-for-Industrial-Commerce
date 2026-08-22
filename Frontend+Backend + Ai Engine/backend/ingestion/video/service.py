import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.config import settings
from backend.ingestion.video.schemas import (
    VideoAnalysisRequest,
    VideoAnalysisResponse,
    ProcessingStats,
    ProcessingStatus,
    AnalysisIntent,
)
from backend.ingestion.video.ingester import VideoIngestionService, VideoIngestionError
from backend.ingestion.video.decoder import VideoDecoderService
from backend.ingestion.video.frame_selector import IntelligentFrameSelector
from backend.ingestion.video.vision import VisionAnalysisService
from backend.ingestion.video.ocr import OCRService
from backend.ingestion.video.speech import SpeechToTextService
from backend.ingestion.video.temporal import TemporalAnalysisService
from backend.ingestion.video.evidence import MultimodalEvidenceBuilder
from backend.ingestion.video.confidence import ConfidenceService
from backend.schemas.ai_contract import AIProcessingMode

class VideoIntelligenceService:
    """
    Main Orchestrator Service for Video Intelligence.
    Executes the multimodal pipeline:
    INGEST -> DECODE -> KEYFRAMES -> AUDIO -> VISION -> OCR -> STT -> TEMPORAL -> EVIDENCE BUILDER -> CONFIDENCE.
    """

    def __init__(self, ai_mode: AIProcessingMode = AIProcessingMode.AUTO):
        self.ai_mode = ai_mode
        self.ingester = VideoIngestionService()
        self.decoder = VideoDecoderService()
        self.frame_selector = IntelligentFrameSelector(self.decoder)
        self.vision_service = VisionAnalysisService(ai_mode=ai_mode)
        self.ocr_service = OCRService(ai_mode=ai_mode)
        self.stt_service = SpeechToTextService(ai_mode=ai_mode)
        self.temporal_service = TemporalAnalysisService()
        self.evidence_builder = MultimodalEvidenceBuilder()
        self.confidence_service = ConfidenceService()

    async def analyze_video(
        self, request: VideoAnalysisRequest
    ) -> VideoAnalysisResponse:
        """
        Asynchronously executes the full multimodal video analysis pipeline.
        Returns the parsed evidence which can then be persisted.
        """
        start_time = time.time()
        analysis_id = f"anl_{uuid.uuid4().hex[:12]}"

        if not request.video_path:
            raise VideoIngestionError("video_path is required for analysis.")

        video_path = Path(request.video_path).resolve()

        # STEP 2: VIDEO INGESTION & METADATA
        resolved_path, metadata = self.ingester.validate_and_ingest(video_path)

        # STEP 3 & 4: DECODING & INTELLIGENT KEYFRAME SELECTION
        selected_frames = self.frame_selector.select_keyframes(resolved_path, metadata)

        # STEP 7: AUDIO EXTRACTION
        audio_path = None
        if metadata.has_audio:
            audio_path = self.decoder.extract_audio(resolved_path, metadata.video_id)

        # STEP 5: VISUAL ANALYSIS
        observations = await self.vision_service.analyze_frames(selected_frames, metadata)

        # STEP 6: OCR ANALYSIS
        ocr_results = await self.ocr_service.process_frames(selected_frames, metadata)

        # STEP 8: SPEECH-TO-TEXT
        transcripts = await self.stt_service.transcribe_audio(audio_path, metadata)

        # STEP 10: MULTIMODAL EVIDENCE BUILDER
        evidence_records = self.evidence_builder.build_evidence(
            metadata=metadata,
            frames=selected_frames,
            observations=observations,
            ocr_results=ocr_results,
            transcripts=transcripts,
        )

        # STEP 9: TEMPORAL UNDERSTANDING & TIMELINE BUILDER
        timeline = self.temporal_service.build_timeline(
            frames=selected_frames,
            observations=observations,
            ocr_results=ocr_results,
            transcripts=transcripts,
            evidence_list=evidence_records,
        )

        # STEP 16: CONFIDENCE CALCULATOR
        confidence_breakdown = self.confidence_service.calculate_confidence(
            metadata=metadata,
            evidence_list=evidence_records,
        )

        processing_time = round(time.time() - start_time, 2)
        processing_stats = ProcessingStats(
            frames_analyzed=len(selected_frames),
            audio_processed=bool(transcripts),
            ocr_processed=bool(ocr_results),
            duration_seconds=metadata.duration_seconds,
            processing_time_seconds=processing_time,
        )

        return VideoAnalysisResponse(
            analysis_id=analysis_id,
            video_id=metadata.video_id,
            query=request.query or "",
            intent=request.intent or AnalysisIntent.MULTIMODAL,
            summary="Video analysis completed successfully.",
            metadata=metadata,
            status=ProcessingStatus.COMPLETED,
            timeline=timeline,
            evidence=evidence_records,
            confidence=confidence_breakdown,
            processing=processing_stats,
        )
