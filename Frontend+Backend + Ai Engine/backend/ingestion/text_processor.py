import os
from typing import Dict, Any, Optional
from backend.ingestion.processor import SourceProcessor
from backend.schemas.source import ProcessedSource

class TextProcessor(SourceProcessor):
    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        meta = metadata or {}
        filename = os.path.basename(file_path)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        return ProcessedSource(
            source_id=source_id,
            original_file=filename,
            source_type="text",
            extracted_text=content,
            metadata={
                **meta,
                "file_size": os.path.getsize(file_path),
                "char_count": len(content),
            },
            pages=1,
            tables=[],
            images=[],
            timestamps=[]
        )
