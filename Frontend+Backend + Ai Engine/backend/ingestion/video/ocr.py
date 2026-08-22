import logging
import uuid
from typing import List, Optional
from pathlib import Path

from pydantic import BaseModel
from backend.ingestion.video.schemas import SelectedFrame, OCRResult, VideoMetadata
from backend.integration.engine_service import resolve_ai_policy, _create_ai_provider
from backend.schemas.ai_contract import AIProcessingMode

logger = logging.getLogger(__name__)


class OCRResponse(BaseModel):
    results: List[OCRResult]


class OCRService:
    """
    Orchestrates visible text detection using the canonical AI routing system (EngineService).
    """

    def __init__(self, ai_mode: AIProcessingMode = AIProcessingMode.AUTO):
        self.ai_mode = ai_mode

    async def process_frames(
        self, frames: List[SelectedFrame], metadata: VideoMetadata
    ) -> List[OCRResult]:
        all_ocr: List[OCRResult] = []
        policy = resolve_ai_policy(self.ai_mode)

        for frame in frames:
            if not Path(frame.file_reference).exists():
                logger.warning(f"Frame file not found for OCR: {frame.file_reference}")
                continue

            prompt = (
                "Extract all visible text from this image. "
                "Output strictly valid JSON containing an array of 'results', each with text, confidence, and approximate bounding box [x, y, width, height] as floats between 0 and 1."
            )

            policy = resolve_ai_policy(self.ai_mode)
            provider = _create_ai_provider(policy)

            try:
                response_dict = await provider.analyze_multimodal(
                    prompt=prompt,
                    image_paths=[frame.file_reference],
                    response_schema=OCRResponse.model_json_schema(),
                    temperature=0.1
                )

                results_data = response_dict.get("results", [])
                for res_data in results_data:
                    if isinstance(res_data, str):
                        continue
                        
                    all_ocr.append(
                        OCRResult(
                            ocr_id=res_data.get("ocr_id", f"ocr_{uuid.uuid4().hex[:8]}"),
                            frame_id=frame.frame_id,
                            timestamp=frame.timestamp,
                            text=res_data.get("text", "").strip(),
                            confidence=float(res_data.get("confidence", 0.90)),
                            bbox=res_data.get("bbox", [0.0, 0.0, 1.0, 1.0])
                        )
                    )
            except Exception as e:
                logger.error(f"OCR failed for frame {frame.frame_id}: {e}")

        return all_ocr
