import uuid
from typing import List, Dict, Any
from backend.ingestion.pdf.schemas import (
    PDFDocumentChunk,
    ChunkContentType,
    PDFPageNode,
    PDFTable,
    PDFImageNode,
    PDFOCRBlock,
    TextBlock,
)


class PDFChunker:
    """
    Document-Boundary & Table-Aware Chunker.
    Splits document content along semantic boundaries (sections, paragraphs, tables, figure captions)
    and ensures table chunks explicitly repeat column headers and row context.
    """

    def generate_chunks(self, document_id: str, page_nodes: List[PDFPageNode]) -> List[PDFDocumentChunk]:
        """
        Generates intelligent, traceable chunks across all pages of a PDF document.
        """
        chunks: List[PDFDocumentChunk] = []

        for page_node in page_nodes:
            p_num = page_node.page_number

            # 1. Text Blocks Chunking
            for block in page_node.text_blocks:
                ctype = self._map_block_type_to_chunk_type(block.block_type)
                chunk_id = f"chk_txt_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                chunks.append(
                    PDFDocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=p_num,
                        section=block.section,
                        content_type=ctype,
                        text=block.text,
                        source="text_extractor",
                        metadata={
                            "block_id": block.block_id,
                            "reading_order_idx": block.reading_order_idx,
                            "block_type": block.block_type,
                        },
                    )
                )

            # 2. Table-Aware Chunking (Repeats headers per row/chunk for LLM context)
            for table in page_node.tables:
                table_chunks = self._chunk_table_with_headers(document_id, table)
                chunks.extend(table_chunks)

            # 3. Image & Visual Observation Chunking
            for img in page_node.images:
                obs_parts = []
                if img.visual_summary:
                    obs_parts.append(f"Visual Summary: {img.visual_summary}")
                
                if img.ocr_blocks:
                    img_ocr_str = "; ".join([b.text for b in img.ocr_blocks if b.text])
                    if img_ocr_str:
                        obs_parts.append(f"Image OCR Text: '{img_ocr_str}'")

                if img.image_evidence:
                    obs_items_str = "; ".join([f"[{o.observation_type}]: {o.value}" for o in img.image_evidence])
                    obs_parts.append(f"Observations: {obs_items_str}")
                elif img.vision_observations:
                    obs_items_str = "; ".join([o.get("value", "") for o in img.vision_observations if o.get("value")])
                    obs_parts.append(f"Observations: {obs_items_str}")

                combined_obs_text = " | ".join(obs_parts)
                chunk_id = f"chk_img_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                chunks.append(
                    PDFDocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=p_num,
                        section=img.section or f"Page {p_num}",
                        content_type=ChunkContentType.DIAGRAM if img.classification.value in ["technical_diagram", "schematic", "diagram", "flowchart", "technical_drawing"] else ChunkContentType.IMAGE,
                        text=f"IMAGE [{img.classification.value.upper()}] (Page {p_num}): {img.caption or ''}. {combined_obs_text}".strip(),
                        source="image_extractor",
                        metadata={
                            "image_id": img.image_id,
                            "classification": img.classification.value,
                            "storage_path": img.storage_path,
                            "quality_assessment": img.quality_assessment,
                            "ocr_text_count": len(img.ocr_blocks),
                        },
                    )
                )

            # 4. OCR Blocks Chunking
            for ocr in page_node.ocr_blocks:
                chunk_id = f"chk_ocr_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                chunks.append(
                    PDFDocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=p_num,
                        section=f"Page {p_num} (Scanned)",
                        content_type=ChunkContentType.OCR,
                        text=ocr.text,
                        source="ocr_engine",
                        metadata={
                            "ocr_id": ocr.ocr_id,
                            "confidence": ocr.confidence,
                            "is_uncertain": ocr.is_uncertain,
                            "strategy": ocr.strategy_used,
                        },
                    )
                )

        return chunks

    def _chunk_table_with_headers(self, document_id: str, table: PDFTable) -> List[PDFDocumentChunk]:
        """
        Table-Aware Chunking: Splits table rows while injecting full table title, column headers,
        and unit context into EVERY chunk so retrieved chunks maintain full context.
        """
        chunks: List[PDFDocumentChunk] = []

        # 1. Full Table Summary Chunk
        summary_chunk_id = f"chk_tbl_sum_{document_id}_p{table.page_number}_{uuid.uuid4().hex[:6]}"
        chunks.append(
            PDFDocumentChunk(
                chunk_id=summary_chunk_id,
                document_id=document_id,
                page_number=table.page_number,
                section=table.section or f"Page {table.page_number}",
                content_type=ChunkContentType.TABLE,
                text=table.text_representation,
                source="table_extractor",
                metadata={
                    "table_id": table.table_id,
                    "columns": table.columns,
                    "row_count": len(table.rows),
                },
            )
        )

        # 2. Row-Level Header-Injected Chunks
        for idx, row in enumerate(table.rows, start=1):
            row_items = []
            for col in table.columns:
                val = row.get(col, "")
                unit_str = f" ({table.units[col]})" if col in table.units else ""
                row_items.append(f"{col}{unit_str}: {val}")

            row_chunk_text = (
                f"TABLE: {table.title} (Page {table.page_number}) | Row {idx}: " + " | ".join(row_items)
            )

            row_chunk_id = f"chk_tbl_row_{document_id}_p{table.page_number}_r{idx}_{uuid.uuid4().hex[:4]}"
            chunks.append(
                PDFDocumentChunk(
                    chunk_id=row_chunk_id,
                    document_id=document_id,
                    page_number=table.page_number,
                    section=table.section or f"Page {table.page_number}",
                    content_type=ChunkContentType.TABLE,
                    text=row_chunk_text,
                    source="table_extractor_row",
                    metadata={
                        "table_id": table.table_id,
                        "row_index": idx,
                        "columns": table.columns,
                    },
                )
            )

        return chunks

    def _map_block_type_to_chunk_type(self, block_type: str) -> ChunkContentType:
        mapping = {
            "heading": ChunkContentType.HEADER,
            "subheading": ChunkContentType.HEADER,
            "paragraph": ChunkContentType.TEXT,
            "bullet_list": ChunkContentType.LIST,
            "numbered_list": ChunkContentType.LIST,
            "caption": ChunkContentType.CAPTION,
            "footnote": ChunkContentType.FOOTNOTE,
        }
        return mapping.get(block_type, ChunkContentType.TEXT)
