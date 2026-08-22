import os
import csv
from typing import Dict, Any, Optional, List
from backend.ingestion.processor import SourceProcessor
from backend.schemas.source import ProcessedSource
from backend.core.logging import logger

class DocumentProcessor(SourceProcessor):
    """
    Processes document-type source files (CSV, XLSX, PDF, DOC, TXT).

    RULES:
    1. CSV: Actually reads and extracts CSV content.
    2. XLSX: Returns extraction_unavailable status (no openpyxl engine configured).
    3. PDF: Returns extraction_unavailable status (no PDF extraction engine configured).
    4. DOC/DOCX: Returns extraction_unavailable status (no docx engine configured).
    5. TXT and other text: Reads actual file content.

    NEVER fabricates product data. If extraction is unavailable, returns a
    structured status indicating the limitation.
    """

    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        meta = metadata or {}
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        extracted_text = ""
        tables: List[Dict[str, Any]] = []
        pages_count = 1

        if ext in ['.csv']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if rows:
                        headers = rows[0]
                        tables.append({"header": headers, "rows": rows[1:50]})
                        extracted_text = f"CSV Document {filename}\nHeaders: {', '.join(headers)}\nRows: {len(rows)-1}\n"
                        for i, r in enumerate(rows[1:20]):
                            extracted_text += f"Row {i+1}: {', '.join(r)}\n"
            except Exception as e:
                logger.error(f"Error reading CSV {file_path}: {e}")
                extracted_text = f"[extraction_error] CSV file {filename} could not be parsed: {e}"

        elif ext in ['.xlsx', '.xls']:
            # Extraction engine (openpyxl) not configured — return structured unavailable status
            extracted_text = (
                f"[extraction_unavailable] Excel Spreadsheet: {filename}\n"
                f"Reason: Excel extraction engine is not configured.\n"
                f"File size: {os.path.getsize(file_path)} bytes\n"
                f"Extension: {ext}\n"
                f"The file has been stored and can be processed when an extraction engine is available."
            )

        elif ext in ['.pdf']:
            try:
                from pathlib import Path
                from backend.ingestion.pdf.service import PDFIntelligenceService
                from backend.ingestion.pdf.adapter import PDFToMainAIAdapter

                pdf_service = PDFIntelligenceService()
                analysis_result = pdf_service.process_pdf(Path(file_path))
                processed = PDFToMainAIAdapter.to_processed_source(analysis_result, source_id=source_id)
                processed.metadata.update(meta)
                return processed
            except Exception as e:
                logger.error(f"Error processing PDF document {file_path}: {e}")
                raise e

        elif ext in ['.doc', '.docx']:
            # DOC/DOCX extraction engine not configured — return structured unavailable status
            extracted_text = (
                f"[extraction_unavailable] Word Document: {filename}\n"
                f"Reason: DOCX extraction engine is not configured.\n"
                f"File size: {os.path.getsize(file_path)} bytes\n"
                f"The file has been stored and can be processed when an extraction engine is available."
            )

        else:
            # Plain text — read actual file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                extracted_text = f"[extraction_error] File {filename} could not be read: {e}"

        return ProcessedSource(
            source_id=source_id,
            original_file=filename,
            source_type=ext.replace('.', '') or "document",
            extracted_text=extracted_text,
            metadata={
                **meta,
                "file_size": os.path.getsize(file_path),
                "extension": ext,
            },
            pages=pages_count,
            tables=tables,
            images=[],
            timestamps=[]
        )
