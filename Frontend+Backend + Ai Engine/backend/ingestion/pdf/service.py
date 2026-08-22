import time
import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.config import settings
from backend.ingestion.pdf.schemas import (
    PDFAnalysisResult,
    PDFMetadata,
    ProcessingStatus,
    PDFQueryRequest,
    PDFQueryResponse,
)
from backend.ingestion.pdf.ingester import PDFIngester
from backend.ingestion.pdf.inspector import PDFInspector
from backend.ingestion.pdf.text_extractor import PDFTextExtractor
from backend.ingestion.pdf.table_extractor import PDFTableExtractor
from backend.ingestion.pdf.image_extractor import PDFImageExtractor
from backend.ingestion.pdf.ocr_engine import PDFOCREngine
from backend.ingestion.pdf.chunker import PDFChunker
from backend.ingestion.pdf.evidence_builder import PDFEvidenceBuilder
from backend.ingestion.pdf.retriever import PDFDocumentRetriever
from backend.ingestion.pdf.contract import PDFMainAIContract


class PDFIntelligenceService:
    """
    Main Orchestrator Service for PDF Intelligence inside Main AI backend.
    Executes end-to-end extraction, structure parsing, multi-pass OCR, table formatting,
    chunking, evidence building, RAG indexing, and LLM text generation.
    """

    def __init__(self):
        self.ingester = PDFIngester()
        self.inspector = PDFInspector()
        self.text_extractor = PDFTextExtractor()
        self.table_extractor = PDFTableExtractor()
        self.image_extractor = PDFImageExtractor()
        self.ocr_engine = PDFOCREngine()
        self.chunker = PDFChunker()
        self.evidence_builder = PDFEvidenceBuilder()
        self.retriever = PDFDocumentRetriever()
        self.contract = PDFMainAIContract()
        self.cache: Dict[str, PDFAnalysisResult] = {}

    def process_pdf(self, file_path: Path, metadata: Optional[PDFMetadata] = None) -> PDFAnalysisResult:
        """
        Processes a PDF document through the complete extraction pipeline.
        """
        start_time = time.time()

        # 1. Validation & Metadata Check
        self.ingester.validate_file(file_path)

        if not metadata:
            file_hash = self.ingester.compute_sha256(file_path)
            page_count = self.ingester.get_page_count(file_path)
            
            stem = file_path.stem
            if stem.startswith("doc_"):
                parts = stem.split("_", 2)
                doc_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else stem
            else:
                doc_id = f"doc_{stem}"

            metadata = PDFMetadata(
                document_id=doc_id,
                filename=file_path.name,
                file_hash=file_hash,
                file_size_bytes=file_path.stat().st_size,
                page_count=page_count,
                upload_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                storage_path=str(file_path),
            )

        doc_id = metadata.document_id

        # 2. Document Inspection & Classification
        classification, page_nodes, metadata = self.inspector.inspect_document(file_path, metadata)

        # 3. Normal Text Extraction & Reading Order
        page_nodes = self.text_extractor.extract_page_text(file_path, page_nodes)

        # 4. Table Extraction & Dual Representation
        all_tables = self.table_extractor.extract_tables_from_pages(file_path, page_nodes)

        # 5. Image Detection & Visual Analysis
        all_images = self.image_extractor.extract_images_from_pages(file_path, page_nodes, doc_id)

        # 6. Scanned Page Detection & Multi-Pass OCR
        page_nodes = self.ocr_engine.process_scanned_pages(file_path, page_nodes)
        all_ocr = []
        for p in page_nodes:
            all_ocr.extend(p.ocr_blocks)

        # 7. Semantic & Table-Aware Chunking
        chunks = self.chunker.generate_chunks(doc_id, page_nodes)

        # 8. Evidence Building, Provenance, & Conflict Detection
        evidence, observed_attrs, conflicts = self.evidence_builder.build_evidence(doc_id, metadata.filename, page_nodes)

        # 9. Retrieval Indexing
        self.retriever.index_document_chunks(doc_id, chunks)

        summary = (
            f"PDF Document '{metadata.filename}' classified as {classification.value} with {metadata.page_count} page(s). "
            f"Extracted {len(chunks)} chunk(s), {len(all_tables)} table(s), {len(all_images)} image(s), "
            f"and {len(all_ocr)} OCR block(s). Identified {len(observed_attrs)} observed attribute(s) with {len(conflicts)} conflict(s)."
        )

        elapsed = round(time.time() - start_time, 2)

        result = PDFAnalysisResult(
            document_id=doc_id,
            filename=metadata.filename,
            classification=classification,
            summary=summary,
            llm_text="",
            metadata=metadata,
            pages=page_nodes,
            tables=all_tables,
            images=all_images,
            ocr_content=all_ocr,
            chunks=chunks,
            evidence=evidence,
            observed_attributes=observed_attrs,
            conflicts=conflicts,
            status=ProcessingStatus.COMPLETED,
            processing_time_seconds=elapsed,
        )

        # Output 2: Generate LLM-ready text representation
        result.llm_text = self.contract.generate_deep_document_text(result)

        self._persist_outputs(result)
        self.cache[doc_id] = result

        return result

    def query_document(self, document_id: str, query_req: PDFQueryRequest) -> PDFQueryResponse:
        """
        Executes query-driven retrieval over document chunks and constructs an evidence bundle.
        """
        result = self.get_analysis(document_id)
        if not result:
            raise ValueError(f"No document analysis found for document_id: {document_id}")

        rel_chunks = self.retriever.retrieve_relevant_chunks(
            document_id=document_id,
            query=query_req.query,
            page_number=query_req.page_number,
            section=query_req.section,
            content_types=query_req.content_types,
            top_k=query_req.limit,
        )

        bundle = self.contract.create_evidence_bundle(result, rel_chunks)

        return PDFQueryResponse(
            document_id=document_id,
            query=query_req.query,
            relevant_chunks=rel_chunks,
            evidence_bundle=bundle,
        )

    def get_analysis(self, document_id: str) -> Optional[PDFAnalysisResult]:
        """Retrieves cached or file-persisted document analysis result."""
        if document_id in self.cache:
            return self.cache[document_id]

        artifacts_dir = Path(getattr(settings, "PDF_ARTIFACTS_PATH", "./data_storage/temp_cache/pdf_artifacts"))
        out_path = artifacts_dir / f"{document_id}_pdf_analysis.json"
        if out_path.exists():
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result = PDFAnalysisResult(**data)
                self.cache[document_id] = result
                self.retriever.index_document_chunks(document_id, result.chunks)
                return result
            except Exception:
                pass
        return None

    def _persist_outputs(self, result: PDFAnalysisResult) -> None:
        """Saves machine-readable JSON and LLM-ready text files to storage."""
        artifacts_dir = Path(getattr(settings, "PDF_ARTIFACTS_PATH", "./data_storage/temp_cache/pdf_artifacts"))
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        json_path = artifacts_dir / f"{result.document_id}_pdf_analysis.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)

        txt_path = artifacts_dir / f"{result.document_id}_llm_text.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.llm_text)
