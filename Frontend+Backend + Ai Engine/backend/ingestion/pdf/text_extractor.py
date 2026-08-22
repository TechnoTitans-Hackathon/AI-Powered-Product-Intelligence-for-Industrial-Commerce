import re
import uuid
from pathlib import Path
from typing import List, Tuple, Optional
from backend.ingestion.pdf.schemas import TextBlock, BoundingBox, PDFPageNode


class PDFTextExtractor:
    """
    Extracts text streams while reconstructing reading order and preserving document structure
    (headings, subheadings, paragraphs, bullet lists, numbered lists, captions, footnotes).
    Supports PyMuPDF, PyPDF, pdfplumber, and a pure-Python fallback stream parser.
    """

    def extract_page_text(self, file_path: Path, page_nodes: List[PDFPageNode]) -> List[PDFPageNode]:
        """
        Extracts structured text blocks for each non-scanned page node.
        """
        for page_node in page_nodes:
            if page_node.is_scanned:
                continue

            blocks = self._extract_blocks_for_page(file_path, page_node.page_number)
            page_node.text_blocks = blocks

        return page_nodes

    def _extract_blocks_for_page(self, file_path: Path, page_number: int) -> List[TextBlock]:
        """Extracts text blocks using fitz/pypdf/pdfplumber or fallback stream parser."""
        # 1. Try fitz (PyMuPDF) with layout & reading order reconstruction
        try:
            import fitz
            doc = fitz.open(str(file_path))
            page = doc[page_number - 1]
            page_dict = page.get_text("dict")
            raw_blocks = page_dict.get("blocks", [])
            doc.close()

            text_blocks: List[TextBlock] = []
            order_idx = 0
            current_section = f"Page {page_number}"

            sorted_raw_blocks = sorted(
                [b for b in raw_blocks if "lines" in b],
                key=lambda b: (round(b["bbox"][0] / 200.0), b["bbox"][1])
            )

            for b in sorted_raw_blocks:
                block_text_lines = []
                max_font_size = 0.0

                for line in b.get("lines", []):
                    line_str = "".join([span.get("text", "") for span in line.get("spans", [])]).strip()
                    if line_str:
                        block_text_lines.append(line_str)
                        for span in line.get("spans", []):
                            if span.get("size", 0.0) > max_font_size:
                                max_font_size = span.get("size", 0.0)

                if not block_text_lines:
                    continue

                full_text = "\n".join(block_text_lines)
                parsed_sub_blocks = self._parse_raw_text_into_blocks(full_text, page_number)
                bbox_coords = b.get("bbox", [0, 0, 0, 0])
                bbox_obj = BoundingBox(
                    x0=float(bbox_coords[0]),
                    y0=float(bbox_coords[1]),
                    x1=float(bbox_coords[2]),
                    y1=float(bbox_coords[3]),
                )

                if parsed_sub_blocks:
                    for sub in parsed_sub_blocks:
                        sub.bbox = bbox_obj
                        sub.reading_order_idx = order_idx
                        text_blocks.append(sub)
                        order_idx += 1
                else:
                    block_type, is_sec_change = self._classify_text_block(full_text, max_font_size)
                    if is_sec_change:
                        current_section = full_text.split("\n")[0].strip()

                    text_blocks.append(
                        TextBlock(
                            block_id=f"blk_p{page_number}_{uuid.uuid4().hex[:6]}",
                            page_number=page_number,
                            text=full_text,
                            block_type=block_type,
                            section=current_section,
                            bbox=bbox_obj,
                            reading_order_idx=order_idx,
                        )
                    )
                    order_idx += 1

            if text_blocks:
                return text_blocks
        except Exception:
            pass

        # 2. Try pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            page = reader.pages[page_number - 1]
            raw_text = page.extract_text() or ""
            if raw_text.strip():
                return self._parse_raw_text_into_blocks(raw_text, page_number)
        except Exception:
            pass

        # 3. Pure Python Fallback Stream Parser for unencrypted PDF stream objects
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            bt_blocks = re.findall(r"BT[\s\S]*?\nET", raw_bytes.decode("latin1", errors="ignore"))
            extracted_lines = []
            for bt in bt_blocks:
                str_matches = re.findall(r"\((.*?)\)", bt)
                for s in str_matches:
                    clean_s = s.replace("\\(", "(").replace("\\)", ")").strip()
                    if clean_s and not clean_s.startswith("/F") and not clean_s.startswith("Tj"):
                        extracted_lines.append(clean_s)

            if extracted_lines:
                raw_text = "\n".join(extracted_lines)
                return self._parse_raw_text_into_blocks(raw_text, page_number)
        except Exception:
            pass

        return []

    def _parse_raw_text_into_blocks(self, raw_text: str, page_number: int) -> List[TextBlock]:
        """Parses a plain text stream into structured text blocks by section/heading boundaries."""
        blocks: List[TextBlock] = []
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return blocks

        current_para = []
        current_section = f"Page {page_number}"
        order_idx = 0

        for line in lines:
            block_type, is_sec = self._classify_text_block(line, font_size=0.0)
            if (is_sec or line.lower().startswith("section ") or line.lower().startswith("chapter ")) and current_para:
                blocks.append(
                    TextBlock(
                        block_id=f"blk_p{page_number}_{uuid.uuid4().hex[:6]}",
                        page_number=page_number,
                        text="\n".join(current_para),
                        block_type="paragraph",
                        section=current_section,
                        reading_order_idx=order_idx,
                    )
                )
                order_idx += 1
                current_para = []
                current_section = line

            current_para.append(line)

        if current_para:
            blocks.append(
                TextBlock(
                    block_id=f"blk_p{page_number}_{uuid.uuid4().hex[:6]}",
                    page_number=page_number,
                    text="\n".join(current_para),
                    block_type="paragraph",
                    section=current_section,
                    reading_order_idx=order_idx,
                )
            )

        return blocks

    def _classify_text_block(self, text: str, font_size: float) -> Tuple[str, bool]:
        """Classifies text block into heading, subheading, paragraph, bullet list, numbered list, caption, or footnote."""
        t_clean = text.strip()
        t_lower = t_clean.lower()

        if t_lower.startswith(("figure ", "fig. ", "table ", "chart ", "diagram ")):
            return "caption", False

        if t_clean.startswith(("*", "†", "‡", "1 ", "2 ")) and len(t_clean) < 100 and ("note" in t_lower or "source" in t_lower):
            return "footnote", False

        if re.match(r"^[\bullet\-\*•]\s+", t_clean):
            return "bullet_list", False
        if re.match(r"^\d+[\.\)]\s+", t_clean):
            return "numbered_list", False

        if font_size >= 16.0 or (len(t_clean) < 60 and t_clean.isupper() and not t_clean.endswith(".")):
            return "heading", True

        if font_size >= 12.5 or (len(t_clean) < 80 and t_clean.istitle() and not t_clean.endswith(".")):
            return "subheading", True

        return "paragraph", False
