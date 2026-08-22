from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.schemas.source import ProcessedSource

class SourceProcessor(ABC):
    """
    Common processor interface for all multimodal inputs.
    Every processed source preserves provenance: source_id, file reference,
    source type, extracted content, metadata, page numbers, timestamps, table info, diagram references.
    """

    @abstractmethod
    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        pass
