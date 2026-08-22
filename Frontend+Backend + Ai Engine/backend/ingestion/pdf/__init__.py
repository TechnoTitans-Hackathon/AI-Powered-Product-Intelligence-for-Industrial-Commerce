"""
PDF Ingestion Capability Package.
Integrates standalone PDF Analyzer capabilities directly into Main AI.
"""

from backend.ingestion.pdf.service import PDFIntelligenceService
from backend.ingestion.pdf.adapter import PDFToMainAIAdapter

__all__ = ["PDFIntelligenceService", "PDFToMainAIAdapter"]
