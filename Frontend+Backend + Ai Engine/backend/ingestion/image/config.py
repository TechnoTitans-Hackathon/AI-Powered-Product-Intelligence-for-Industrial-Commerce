"""Configuration settings for the Image Intelligence Module."""

from __future__ import annotations

import os
from typing import Set
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ImageIntelligenceConfig(BaseModel):
    """Configuration parameters for image processing, OCR, vision, and LLM reasoning."""

    # Allowed image MIME types and extensions
    ALLOWED_MIME_TYPES: Set[str] = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
    ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}

    # File size limits (in bytes) - default 20 MB
    MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024

    # Image dimension constraints
    MAX_DIMENSION_PX: int = 2048
    MIN_DIMENSION_PX: int = 32

    # OCR settings
    OCR_LANGUAGES: list[str] = ["en"]
    OCR_CONFIDENCE_THRESHOLD: float = 0.2
    OCR_GPU: bool = False  # Default to CPU to ensure universal compatibility

    # Vision & LLM settings
    DEFAULT_VISION_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    DEFAULT_TEMPERATURE: float = 0.1
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "offline")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


config = ImageIntelligenceConfig()
