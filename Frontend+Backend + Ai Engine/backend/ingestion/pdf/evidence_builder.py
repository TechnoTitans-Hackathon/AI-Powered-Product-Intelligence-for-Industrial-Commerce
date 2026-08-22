import uuid
from typing import List, Dict, Any, Tuple
from backend.ingestion.pdf.schemas import (
    PDFPageNode,
    AttributeEvidence,
    AttributeStatus,
    ConflictRecord,
    PDFDocumentChunk,
    EvidenceRecord,
    EvidenceType,
)


class PDFEvidenceBuilder:
    """
    Transforms extracted document elements into canonical, traceable EvidenceRecord objects,
    distinguishes OBSERVED / INFERRED / UNKNOWN status, and performs cross-page conflict detection.
    """

    def build_evidence(
        self, document_id: str, filename: str, page_nodes: List[PDFPageNode]
    ) -> Tuple[List[EvidenceRecord], List[AttributeEvidence], List[ConflictRecord]]:
        """
        Builds traceable EvidenceRecords, observed attribute list, and conflict records.
        """
        evidence_list: List[EvidenceRecord] = []
        observed_attrs: List[AttributeEvidence] = []
        attribute_page_map: Dict[str, List[Dict[str, Any]]] = {}

        for page_node in page_nodes:
            p_num = page_node.page_number

            # 1. Text Evidence
            for block in page_node.text_blocks:
                ev_id = f"ev_pdf_txt_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                evidence_list.append(
                    EvidenceRecord(
                        evidence_id=ev_id,
                        type=EvidenceType.TEXT,
                        timestamp_start=float(p_num),
                        timestamp_end=float(p_num),
                        frame_id=f"page_{p_num}",
                        content=f"Page {p_num} [{block.block_type}]: {block.text}",
                        confidence=1.0,
                        source="pdf_text_extractor",
                        metadata={
                            "document_id": document_id,
                            "page": p_num,
                            "section": block.section,
                            "block_type": block.block_type,
                        },
                    )
                )

                # Extract key-value patterns for observed attributes
                parsed_attrs = self._extract_observed_key_values(block.text, p_num, "text")
                for attr in parsed_attrs:
                    observed_attrs.append(attr)
                    self._map_attribute_variation(attribute_page_map, attr)

            # 2. Table Evidence
            for table in page_node.tables:
                ev_id = f"ev_pdf_tbl_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                evidence_list.append(
                    EvidenceRecord(
                        evidence_id=ev_id,
                        type=EvidenceType.TABLE,
                        timestamp_start=float(p_num),
                        timestamp_end=float(p_num),
                        frame_id=f"page_{p_num}",
                        content=table.text_representation,
                        confidence=0.98,
                        source="pdf_table_extractor",
                        metadata={
                            "document_id": document_id,
                            "page": p_num,
                            "table_id": table.table_id,
                            "columns": table.columns,
                            "row_count": len(table.rows),
                        },
                    )
                )

                # Extract observed attributes from table rows
                for row in table.rows:
                    for col_name, val in row.items():
                        if val and str(val).strip():
                            unit_str = table.units.get(col_name)
                            attr = AttributeEvidence(
                                attribute_name=col_name,
                                value=str(val).strip(),
                                unit=unit_str,
                                status=AttributeStatus.OBSERVED,
                                page_number=p_num,
                                source_type="table",
                                confidence=0.98,
                                raw_snippet=f"{col_name}: {val} {unit_str or ''}".strip(),
                            )
                            observed_attrs.append(attr)
                            self._map_attribute_variation(attribute_page_map, attr)

            # 3. Image / Visual Evidence
            for img in page_node.images:
                for img_ocr in img.ocr_blocks:
                    ev_ocr_id = f"ev_pdf_img_ocr_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                    evidence_list.append(
                        EvidenceRecord(
                            evidence_id=ev_ocr_id,
                            type=EvidenceType.OCR,
                            timestamp_start=float(p_num),
                            timestamp_end=float(p_num),
                            frame_id=f"page_{p_num}",
                            content=f"Image {img.image_id} OCR Text: {img_ocr.text}",
                            confidence=img_ocr.confidence,
                            source="pdf_image_ocr",
                            metadata={
                                "document_id": document_id,
                                "page": p_num,
                                "image_id": img.image_id,
                                "ocr_id": img_ocr.ocr_id,
                            },
                        )
                    )

                ev_id = f"ev_pdf_img_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                summary_str = img.visual_summary or ""
                obs_text = "; ".join([o.value for o in img.image_evidence]) if img.image_evidence else "; ".join([o.get("value", "") for o in img.vision_observations if o.get("value")])
                content_str = f"Image [{img.classification.value.upper()}] on Page {p_num}: {img.caption or ''}. Summary: {summary_str}. Visual Observations: {obs_text}"
                
                evidence_list.append(
                    EvidenceRecord(
                        evidence_id=ev_id,
                        type=EvidenceType.VISUAL,
                        timestamp_start=float(p_num),
                        timestamp_end=float(p_num),
                        frame_id=f"page_{p_num}",
                        content=content_str,
                        confidence=0.90 if not img.quality_assessment.get("is_low_quality") else 0.70,
                        source="pdf_image_extractor",
                        metadata={
                            "document_id": document_id,
                            "page": p_num,
                            "image_id": img.image_id,
                            "classification": img.classification.value,
                            "storage_path": img.storage_path,
                            "quality_assessment": img.quality_assessment,
                        },
                    )
                )

            # 4. OCR Evidence
            for ocr in page_node.ocr_blocks:
                ev_id = f"ev_pdf_ocr_{document_id}_p{p_num}_{uuid.uuid4().hex[:6]}"
                evidence_list.append(
                    EvidenceRecord(
                        evidence_id=ev_id,
                        type=EvidenceType.OCR,
                        timestamp_start=float(p_num),
                        timestamp_end=float(p_num),
                        frame_id=f"page_{p_num}",
                        content=f"Scanned Page {p_num} Visible Text: {ocr.text}",
                        confidence=ocr.confidence,
                        source="pdf_ocr_engine",
                        metadata={
                            "document_id": document_id,
                            "page": p_num,
                            "ocr_id": ocr.ocr_id,
                            "is_uncertain": ocr.is_uncertain,
                            "strategy": ocr.strategy_used,
                        },
                    )
                )

        conflicts = self._detect_conflicts(attribute_page_map)
        return evidence_list, observed_attrs, conflicts

    def _map_attribute_variation(self, attr_map: Dict[str, List[Dict[str, Any]]], attr: AttributeEvidence):
        key = attr.attribute_name.strip().lower()
        if key not in attr_map:
            attr_map[key] = []
        attr_map[key].append({
            "page": attr.page_number,
            "value": attr.value,
            "unit": attr.unit,
            "snippet": attr.raw_snippet,
        })

    def _detect_conflicts(self, attr_map: Dict[str, List[Dict[str, Any]]]) -> List[ConflictRecord]:
        conflicts = []
        for attr_name, items in attr_map.items():
            if len(items) < 2:
                continue

            unique_vals = set(i["value"] for i in items if i["value"])
            if len(unique_vals) > 1:
                conflicts.append(
                    ConflictRecord(
                        conflict_id=f"conf_{uuid.uuid4().hex[:6]}",
                        attribute_or_topic=attr_name.title(),
                        variations=items,
                        message=f"Attribute '{attr_name.title()}' appears with different values across pages: {list(unique_vals)}",
                    )
                )
        return conflicts

    def _extract_observed_key_values(self, text: str, page_number: int, source_type: str) -> List[AttributeEvidence]:
        attrs = []
        lines = text.split("\n")
        for line in lines:
            if ":" in line or "=" in line:
                delim = ":" if ":" in line else "="
                parts = line.split(delim, 1)
                k = parts[0].strip(" -*")
                v = parts[1].strip()
                if 2 <= len(k) <= 40 and v:
                    attrs.append(
                        AttributeEvidence(
                            attribute_name=k,
                            value=v,
                            status=AttributeStatus.OBSERVED,
                            page_number=page_number,
                            source_type=source_type,
                            confidence=1.0,
                            raw_snippet=line.strip(),
                        )
                    )
        return attrs
