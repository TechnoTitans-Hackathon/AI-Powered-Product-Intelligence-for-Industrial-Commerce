import uuid
from typing import List, Dict, Any
from backend.schemas.source import ProcessedSource

class DocumentChunker:
    """
    Chunks processed sources into indexable units while preserving
    provenance metadata: source_id, document_id, page, timestamp, URL, content.
    """

    def chunk_source(self, processed: ProcessedSource, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        text = processed.extracted_text
        chunks = []

        if not text:
            return chunks

        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        page_number = 1

        for line in lines:
            if line.startswith("Page "):
                # Try to extract page number
                try:
                    parts = line.split()
                    page_number = int(parts[1].replace(':', ''))
                except (IndexError, ValueError):
                    pass

            current_chunk.append(line)
            current_length += len(line)

            if current_length >= chunk_size:
                chunk_text = "\n".join(current_chunk)
                chunk_id = f"chunk_{uuid.uuid4().hex[:10]}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "source_id": processed.source_id,
                    "document_name": processed.original_file,
                    "page": page_number,
                    "content": chunk_text,
                    "metadata": {
                        **processed.metadata,
                        "source_type": processed.source_type,
                        "original_file": processed.original_file
                    }
                })
                # Retain overlap
                current_chunk = current_chunk[-2:] if len(current_chunk) > 2 else []
                current_length = sum(len(l) for l in current_chunk)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunk_id = f"chunk_{uuid.uuid4().hex[:10]}"
            chunks.append({
                "chunk_id": chunk_id,
                "source_id": processed.source_id,
                "document_name": processed.original_file,
                "page": page_number,
                "content": chunk_text,
                "metadata": {
                    **processed.metadata,
                    "source_type": processed.source_type,
                    "original_file": processed.original_file
                }
            })

        return chunks

chunker = DocumentChunker()
