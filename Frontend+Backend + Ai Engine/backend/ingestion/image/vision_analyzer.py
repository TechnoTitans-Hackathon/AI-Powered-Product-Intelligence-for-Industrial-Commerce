"""Multimodal Vision Analyzer for Industrial Product Perception."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config
from .prompts import VISION_ANALYSIS_PROMPT, VISION_SYSTEM_INSTRUCTION
from .schemas import (
    ActivityObservation,
    EnvironmentObservation,
    StepStatusEnum,
    VisionOutput,
    VisualObservation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base Interface
# ---------------------------------------------------------------------------

class VisionAnalyzerInterface(ABC):
    """Abstract interface for multimodal vision analysis."""

    @abstractmethod
    async def analyze(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionOutput:
        """Analyze image and extract visual observations."""
        ...


# ---------------------------------------------------------------------------
# Gemini Multimodal Vision Analyzer (Real)
# ---------------------------------------------------------------------------

class GeminiVisionAnalyzer(VisionAnalyzerInterface):
    """
    Real vision analyzer using Google GenAI SDK (`gemini-2.0-flash`).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model or config.DEFAULT_VISION_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured for GeminiVisionAnalyzer.")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("google-genai package required. Install with: pip install google-genai")
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False)
    async def analyze(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionOutput:
        try:
            client = self._get_client()
            from google.genai import types

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

            gen_config = types.GenerateContentConfig(
                temperature=config.DEFAULT_TEMPERATURE,
                response_mime_type="application/json",
                system_instruction=VISION_SYSTEM_INSTRUCTION,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[image_part, VISION_ANALYSIS_PROMPT],
                config=gen_config,
            )

            raw_text = response.text or "{}"
            parsed = self._parse_json(raw_text)

            image_type_val = str(parsed.get("image_type", "PRODUCT_PHOTOGRAPH")).upper()

            # Map raw response to VisionOutput
            obs_list = []
            for item in parsed.get("visual_observations", []):
                if isinstance(item, dict) and "observation" in item:
                    obs_list.append(
                        VisualObservation(
                            observation=str(item["observation"]),
                            confidence=min(1.0, max(0.0, float(item.get("confidence", 0.9)))),
                            category=item.get("category"),
                            location_hint=item.get("location_hint"),
                        )
                    )

            comp_rels = []
            for rel in parsed.get("component_relationships", []):
                if isinstance(rel, dict) and "name" in rel:
                    comp_rels.append(
                        ComponentRelationship(
                            name=str(rel["name"]),
                            type=str(rel.get("type", "component")),
                            label=rel.get("label", str(rel["name"])),
                            target_component=rel.get("target_component", str(rel["name"])),
                            relationship=str(rel.get("relationship", "LABELS")),
                            confidence=min(1.0, max(0.0, float(rel.get("confidence", 0.9)))),
                            source=str(rel.get("source", "OCR+VISION")),
                            evidence=rel.get("evidence"),
                        )
                    )

            env = None
            if "environment" in parsed and isinstance(parsed["environment"], dict):
                env_desc = parsed["environment"].get("description")
                if env_desc:
                    env = EnvironmentObservation(
                        description=str(env_desc),
                        confidence=min(1.0, max(0.0, float(parsed["environment"].get("confidence", 0.85)))),
                    )

            activities = []
            for act in parsed.get("activities", []):
                if isinstance(act, dict) and "description" in act:
                    activities.append(
                        ActivityObservation(
                            description=str(act["description"]),
                            confidence=min(1.0, max(0.0, float(act.get("confidence", 0.8)))),
                        )
                    )

            visible_labels = [str(lbl) for lbl in parsed.get("visible_labels", []) if lbl]

            return VisionOutput(
                image_type=image_type_val,
                visual_observations=obs_list,
                component_relationships=comp_rels,
                environment=env,
                activities=activities,
                visible_labels=visible_labels,
                status=StepStatusEnum.COMPLETED,
            )

        except Exception as e:
            logger.error(f"GeminiVisionAnalyzer: analysis failed — {e}", exc_info=True)
            return VisionOutput(
                image_type="UNKNOWN",
                visual_observations=[],
                status=StepStatusEnum.FAILED,
                error_message=str(e),
            )

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Safely parses and repairs JSON from model output."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            s = text.find("{")
            e = text.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(text[s : e + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Could not parse vision JSON: {text[:200]}")
            return {}



# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_vision_analyzer(provider: Optional[str] = None) -> VisionAnalyzerInterface:
    """Creates the vision analyzer according to environment or provider argument."""
    selected_provider = (provider or config.AI_PROVIDER or "").lower()
    api_key = config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if selected_provider == "gemini" and api_key:
        logger.info("Using GeminiVisionAnalyzer with real API.")
        return GeminiVisionAnalyzer(api_key=api_key)

    logger.error("Vision Inference Unavailable: Missing provider or API key.")
    raise RuntimeError("REAL VISION ENGINE UNAVAILABLE")
