import logging
import uuid
from typing import List, Optional
from pathlib import Path

from pydantic import BaseModel
from backend.ingestion.video.schemas import TranscriptSegment, VideoMetadata
from backend.integration.engine_service import resolve_ai_policy, _create_ai_provider
from backend.schemas.ai_contract import AIProcessingMode

logger = logging.getLogger(__name__)


class TranscriptionResponse(BaseModel):
    segments: List[TranscriptSegment]


class SpeechToTextService:
    """
    Orchestrates speech transcription using the canonical AI routing system (EngineService).
    """

    def __init__(self, ai_mode: AIProcessingMode = AIProcessingMode.AUTO):
        self.ai_mode = ai_mode

    async def transcribe_audio(
        self, audio_path: Optional[Path], metadata: VideoMetadata
    ) -> List[TranscriptSegment]:
        if not metadata.has_audio or audio_path is None or not audio_path.exists():
            return []

        prompt = (
            "Transcribe the provided audio file. "
            "Identify the speakers if possible and generate timestamped text segments. "
            "Output strictly valid JSON with an array of segments, each containing start, end, text, confidence, and speaker."
        )
        policy = resolve_ai_policy(self.ai_mode)
        provider = _create_ai_provider(policy)

        try:
            response_dict = await provider.analyze_multimodal(
                prompt=prompt,
                audio_paths=[str(audio_path)],
                response_schema=TranscriptionResponse.model_json_schema(),
                temperature=0.1
            )
            
            segments_data = response_dict.get("segments", [])
            segments: List[TranscriptSegment] = []
            
            for seg in segments_data:
                # Handle fallback cases
                if isinstance(seg, str):
                    continue
                
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start + 2.0))
                
                segments.append(
                    TranscriptSegment(
                        segment_id=seg.get("segment_id", f"seg_{uuid.uuid4().hex[:8]}"),
                        start=round(start, 2),
                        end=round(end, 2),
                        text=seg.get("text", "").strip(),
                        confidence=float(seg.get("confidence", 0.90)),
                        speaker=seg.get("speaker", "Unknown")
                    )
                )
            return segments
        except Exception as e:
            logger.error(f"Speech transcription failed via EngineService: {e}")
            return []
