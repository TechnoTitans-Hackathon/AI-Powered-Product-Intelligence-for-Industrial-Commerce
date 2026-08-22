from typing import Dict, Any, List
from backend.ingestion.pdf.schemas import (
    PDFAnalysisResult,
    DocumentEvidenceBundle,
    PDFDocumentChunk,
)


class PDFMainAIContract:
    """
    Exposes a standardized contract / adapter interface for Main AI LLM consumption.
    Ensures the PDF module prepares clean, traceable evidence bundles.
    """

    def create_evidence_bundle(
        self,
        analysis_result: PDFAnalysisResult,
        relevant_chunks: List[PDFDocumentChunk],
    ) -> DocumentEvidenceBundle:
        """
        Creates a DocumentEvidenceBundle context package tailored for LLM consumption.
        """
        rel_content = [
            {
                "chunk_id": chk.chunk_id,
                "content": chk.text,
                "content_type": chk.content_type.value,
                "page": chk.page_number,
                "section": chk.section,
                "source": chk.source,
                "relevance_score": chk.relevance_score,
                "metadata": chk.metadata,
            }
            for chk in relevant_chunks
        ]

        return DocumentEvidenceBundle(
            document_id=analysis_result.document_id,
            filename=analysis_result.filename,
            document_type="pdf",
            classification=analysis_result.classification,
            summary=analysis_result.summary,
            relevant_content=rel_content,
            tables=analysis_result.tables,
            ocr_content=analysis_result.ocr_content,
            visual_evidence=analysis_result.images,
            evidence=analysis_result.evidence,
            conflicts=analysis_result.conflicts,
            metadata=analysis_result.metadata.model_dump(),
        )

    def extract_canonical_evidence(self, analysis_result: PDFAnalysisResult) -> List[Dict[str, Any]]:
        """
        Converts PDF evidence records into canonical evidence items.
        """
        canonical_items = []
        for ev in analysis_result.evidence:
            canonical_items.append(
                {
                    "evidence_id": ev.evidence_id,
                    "document_id": analysis_result.document_id,
                    "modality_type": ev.type.value,
                    "page_number": int(ev.timestamp_start) if ev.timestamp_start else 1,
                    "content": ev.content,
                    "confidence": ev.confidence,
                    "source": ev.source,
                    "provenance": {
                        "filename": analysis_result.filename,
                        "document_id": analysis_result.document_id,
                    },
                    "metadata": ev.metadata,
                }
            )
        return canonical_items

    def generate_deep_document_text(self, analysis_result: PDFAnalysisResult) -> str:
        """
        Generates LLM-ready text representation for Main AI.
        """
        lines = [
            f"DOCUMENT: {analysis_result.filename}",
            f"DOCUMENT ID: {analysis_result.document_id}",
            f"CLASSIFICATION: {analysis_result.classification.value}",
            "=" * 60,
            "",
        ]

        for p_node in analysis_result.pages:
            lines.append(f"--- PAGE {p_node.page_number} ---")
            lines.append("")

            # Text blocks
            for blk in p_node.text_blocks:
                lines.append(f"[{blk.block_type.upper()}] (Section: {blk.section or 'N/A'}):")
                lines.append(blk.text)
                lines.append("")

            # Tables
            for tbl in p_node.tables:
                lines.append(tbl.text_representation)

            # Images & Diagrams
            for img in p_node.images:
                lines.append(f"FIGURE [{img.classification.value.upper()}] (Image ID: {img.image_id}): {img.caption or ''}")
                
                if img.quality_assessment:
                    q_res = img.quality_assessment.get("resolution_status", "unknown")
                    q_blur = img.quality_assessment.get("blur_score", 100)
                    q_low = img.quality_assessment.get("is_low_quality", False)
                    lines.append(f"IMAGE QUALITY: Resolution={q_res}, BlurScore={q_blur}, LowQualityFlag={q_low}")

                if img.ocr_blocks:
                    lines.append("IMAGE OCR TEXT:")
                    for img_ocr in img.ocr_blocks:
                        lines.append(f"  - '{img_ocr.text}' (Confidence: {img_ocr.confidence})")

                if img.visual_summary:
                    lines.append(f"VISUAL SUMMARY: {img.visual_summary}")

                if img.image_evidence:
                    lines.append("DEEP VISUAL OBSERVATIONS:")
                    for obs in img.image_evidence:
                        lines.append(f"  - [{obs.observation_type}]: {obs.value} (Confidence: {obs.confidence}, Source: {obs.source_type})")
                elif img.vision_observations:
                    obs_str = "; ".join([o.get("value", "") for o in img.vision_observations if o.get("value")])
                    lines.append(f"VISUAL ANALYSIS: {obs_str}")

                lines.append("")

            # OCR blocks
            for ocr in p_node.ocr_blocks:
                lines.append(f"[SCANNED OCR (Confidence: {ocr.confidence})]: {ocr.text}")
                lines.append("")

        if analysis_result.conflicts:
            lines.append("=" * 60)
            lines.append("CONFLICTS / VARIATIONS DETECTED:")
            for conf in analysis_result.conflicts:
                lines.append(f"- {conf.message}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("END OF EVIDENCE DOCUMENT")
        return "\n".join(lines)
