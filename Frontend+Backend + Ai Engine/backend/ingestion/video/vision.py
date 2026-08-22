import logging
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from backend.core.config import settings
from backend.ingestion.video.schemas import VideoMetadata, SelectedFrame
from backend.integration.engine_service import resolve_ai_policy, _create_ai_provider
from backend.schemas.ai_contract import AIProcessingMode

logger = logging.getLogger(__name__)

class VisionObservation(BaseModel):
    """A single visual observation from a video frame."""
    frame_id: str
    timestamp: float
    observation_type: str = Field(description="'object', 'action', 'scene', 'technical_info', 'diagram'")
    value: str
    confidence: float

class VisionAnalysisResponse(BaseModel):
    observations: List[VisionObservation]

class VisionAnalysisService:
    """
    Orchestrates frame analysis using the canonical AI routing system (EngineService).
    """
    def __init__(self, ai_mode: AIProcessingMode = AIProcessingMode.AUTO):
        self.ai_mode = ai_mode

    async def analyze_frames(
        self, frames: List[SelectedFrame], metadata: VideoMetadata
    ) -> List[VisionObservation]:
        """
        Analyze a list of frames using the configured agent1_provider.
        """
        all_observations: List[VisionObservation] = []
        
        # Resolve policy based on mode
        policy = resolve_ai_policy(self.ai_mode)
        
        for frame in frames:
            if not Path(frame.file_reference).exists():
                logger.warning(f"Frame file not found: {frame.file_reference}")
                continue

            prompt = (
                "Describe the visual content of this video frame objectively. "
                "Identify visible objects, actions, scene setting, and visible technical diagrams/text. "
                "Do NOT assume specific product identity unless clearly visible."
            )
            
            try:
                # Call EngineService.execute_agent1 which uses the provider
                provider = _create_ai_provider(policy)
                
                response_dict = await provider.analyze_multimodal(
                    prompt=prompt,
                    image_paths=[frame.file_reference],
                    response_schema=VisionAnalysisResponse.model_json_schema(),
                    temperature=0.2
                )
                
                # Parse response
                observations_data = response_dict.get("observations", [])
                for obs_data in observations_data:
                    # Enforce missing required fields
                    if "frame_id" not in obs_data:
                        obs_data["frame_id"] = frame.frame_id
                    if "timestamp" not in obs_data:
                        obs_data["timestamp"] = frame.timestamp
                    if "confidence" not in obs_data:
                        obs_data["confidence"] = 0.8
                        
                    # Handle fallback strings gracefully
                    if isinstance(obs_data, str):
                        all_observations.append(
                            VisionObservation(
                                frame_id=frame.frame_id,
                                timestamp=frame.timestamp,
                                observation_type="scene",
                                value=obs_data,
                                confidence=0.5
                            )
                        )
                    else:
                        all_observations.append(VisionObservation(**obs_data))
                        
            except Exception as e:
                logger.error(f"Vision analysis failed for frame {frame.frame_id}: {e}")
                
        return all_observations
