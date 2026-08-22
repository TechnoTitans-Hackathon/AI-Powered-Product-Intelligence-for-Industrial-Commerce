from typing import Dict, Any, Optional
from backend.ingestion.processor import SourceProcessor
from backend.schemas.source import ProcessedSource

class URLProcessor(SourceProcessor):
    """
    Processes URL source inputs.

    RULES:
    1. HTTP fetching engine is not configured — returns extraction_unavailable status.
    2. NEVER fabricates web page content or product specifications.
    3. Preserves the target URL in metadata.
    """

    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        meta = metadata or {}
        target_url = meta.get("url") or file_path

        extracted_text = (
            f"[extraction_unavailable] Web Page: {target_url}\n"
            f"Reason: HTTP fetching engine is not configured.\n"
            f"The URL has been recorded and can be fetched when an HTTP extraction engine is available."
        )

        return ProcessedSource(
            source_id=source_id,
            original_file=target_url,
            source_type="url",
            extracted_text=extracted_text,
            metadata={
                **meta,
                "url": target_url,
                "extraction_status": "unavailable",
                "extraction_reason": "HTTP fetching engine not configured"
            },
            pages=1,
            tables=[],
            images=[],
            timestamps=[]
        )
