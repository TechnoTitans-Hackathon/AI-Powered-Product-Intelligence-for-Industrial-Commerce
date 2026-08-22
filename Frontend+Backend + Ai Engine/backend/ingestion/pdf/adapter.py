from typing import Dict, Any
from backend.schemas.source import ProcessedSource
from backend.ingestion.pdf.schemas import PDFAnalysisResult


class PDFToMainAIAdapter:
    """
    Adapter converting PDFIntelligenceService PDFAnalysisResult into Main AI ProcessedSource.
    Preserves document ID, page numbers, sections, table representations, images, OCR,
    chunks, evidence, provenance, and conflicts.
    """

    @staticmethod
    def to_processed_source(result: PDFAnalysisResult, source_id: str) -> ProcessedSource:
        tables_data = [
            {
                "table_id": tbl.table_id,
                "page_number": tbl.page_number,
                "title": tbl.title,
                "columns": tbl.columns,
                "rows": tbl.rows,
                "units": tbl.units,
                "text_representation": tbl.text_representation,
            }
            for tbl in result.tables
        ]

        images_data = [
            {
                "image_id": img.image_id,
                "page_number": img.page_number,
                "classification": img.classification.value,
                "caption": img.caption,
                "storage_path": img.storage_path,
                "quality_assessment": img.quality_assessment,
                "visual_summary": img.visual_summary,
                "ocr_blocks": [ocr.model_dump() for ocr in img.ocr_blocks],
            }
            for img in result.images
        ]

        chunks_data = [
            {
                "chunk_id": chk.chunk_id,
                "document_id": chk.document_id,
                "page_number": chk.page_number,
                "section": chk.section,
                "content_type": chk.content_type.value,
                "text": chk.text,
                "source": chk.source,
                "relevance_score": chk.relevance_score,
                "metadata": chk.metadata,
            }
            for chk in result.chunks
        ]

        evidence_data = [
            {
                "evidence_id": ev.evidence_id,
                "type": ev.type.value,
                "timestamp_start": ev.timestamp_start,
                "timestamp_end": ev.timestamp_end,
                "frame_id": ev.frame_id,
                "content": ev.content,
                "confidence": ev.confidence,
                "source": ev.source,
                "metadata": ev.metadata,
            }
            for ev in result.evidence
        ]

        return ProcessedSource(
            source_id=source_id,
            original_file=result.filename,
            source_type="pdf",
            extracted_text=result.llm_text or result.summary,
            pages=result.metadata.page_count,
            tables=tables_data,
            images=images_data,
            timestamps=[],
            metadata={
                "pdf_document_id": result.document_id,
                "file_hash": result.metadata.file_hash,
                "file_size": result.metadata.file_size_bytes,
                "classification": result.classification.value,
                "summary": result.summary,
                "processing_time_seconds": result.processing_time_seconds,
                "pdf_chunks": chunks_data,
                "pdf_evidence": evidence_data,
                "observed_attributes": [attr.model_dump() for attr in result.observed_attributes],
                "conflicts": [conf.model_dump() for conf in result.conflicts],
            }
        )
