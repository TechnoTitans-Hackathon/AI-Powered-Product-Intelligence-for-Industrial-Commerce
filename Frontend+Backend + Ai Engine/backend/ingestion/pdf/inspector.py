import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from backend.ingestion.pdf.schemas import (
    DocumentClassification,
    PDFMetadata,
    PDFPageNode,
)


class PDFInspector:
    """
    Inspects PDF pages prior to extraction to determine structural characteristics,
    scanned status, text density, image/table presence, and document classification.
    """

    def inspect_document(
        self, file_path: Path, metadata: PDFMetadata
    ) -> Tuple[DocumentClassification, List[PDFPageNode], PDFMetadata]:
        """
        Inspects PDF pages and returns document classification, initialized PageNode list, and updated PDFMetadata.
        """
        page_nodes: List[PDFPageNode] = []

        title, author, creator, producer = self._extract_pdf_metadata(file_path)

        metadata.title = title or metadata.filename
        metadata.author = author
        metadata.creator = creator
        metadata.producer = producer

        raw_pages_info = self._inspect_pages_raw(file_path, metadata.page_count)

        scanned_count = 0
        text_heavy_count = 0
        image_heavy_count = 0
        table_detected_count = 0

        for idx, page_info in enumerate(raw_pages_info, start=1):
            p_num = page_info["page_number"]
            width = page_info["width"]
            height = page_info["height"]
            char_count = page_info["char_count"]
            image_count = page_info["image_count"]
            has_table_grid = page_info["has_table_grid"]

            # Scanned page heuristic: no native text stream (char_count == 0) or minimal text with raster image
            is_scanned = (char_count == 0) or (char_count < 20 and image_count >= 1)

            if is_scanned:
                scanned_count += 1
            elif char_count > 200:
                text_heavy_count += 1

            if image_count >= 2:
                image_heavy_count += 1

            if has_table_grid:
                table_detected_count += 1

            node = PDFPageNode(
                page_number=p_num,
                width=width,
                height=height,
                text_density=round(float(char_count) / max(1.0, (width * height) / 10000.0), 2),
                is_scanned=is_scanned,
            )
            page_nodes.append(node)

        total_pages = len(page_nodes)
        if total_pages == 0:
            classification = DocumentClassification.UNKNOWN
        elif scanned_count == total_pages:
            classification = DocumentClassification.SCANNED
        elif scanned_count > 0:
            classification = DocumentClassification.MIXED
        elif table_detected_count >= max(1, total_pages // 2):
            classification = DocumentClassification.TECHNICAL_DOCUMENT
        elif image_heavy_count >= max(1, total_pages // 2):
            classification = DocumentClassification.IMAGE_HEAVY
        else:
            classification = DocumentClassification.TEXT

        return classification, page_nodes, metadata

    def _extract_pdf_metadata(self, file_path: Path) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            if reader.metadata:
                m = reader.metadata
                return (
                    m.get("/Title"),
                    m.get("/Author"),
                    m.get("/Creator"),
                    m.get("/Producer"),
                )
        except Exception:
            pass

        try:
            import fitz
            doc = fitz.open(str(file_path))
            m = doc.metadata
            doc.close()
            if m:
                return (m.get("title"), m.get("author"), m.get("creator"), m.get("producer"))
        except Exception:
            pass

        return None, None, None, None

    def _inspect_pages_raw(self, file_path: Path, expected_page_count: int) -> List[Dict[str, Any]]:
        """Extracts basic layout metrics per page."""
        try:
            import fitz
            doc = fitz.open(str(file_path))
            pages = []
            for i, page in enumerate(doc, start=1):
                rect = page.rect
                text = page.get_text()
                image_list = page.get_images()
                has_grid = "|" in text or "\t" in text or "  " in text or len(page.get_drawings()) > 5
                pages.append({
                    "page_number": i,
                    "width": float(rect.width),
                    "height": float(rect.height),
                    "char_count": len(text.strip()),
                    "image_count": len(image_list),
                    "has_table_grid": has_grid,
                })
            doc.close()
            return pages
        except Exception:
            pass

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            pages = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                images = getattr(page, "images", [])
                has_grid = "|" in text or "\t" in text or "  " in text
                pages.append({
                    "page_number": i,
                    "width": float(page.mediabox.width if hasattr(page, "mediabox") else 612),
                    "height": float(page.mediabox.height if hasattr(page, "mediabox") else 792),
                    "char_count": len(text.strip()),
                    "image_count": len(images),
                    "has_table_grid": has_grid,
                })
            return pages
        except Exception:
            pass

        # Pure Python stream inspection for text length & table grid detection
        pages = []
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            bt_blocks = re.findall(r"BT[\s\S]*?\nET", raw_bytes.decode("latin1", errors="ignore"))
            extracted_chars = 0
            has_grid = False
            for bt in bt_blocks:
                str_matches = re.findall(r"\((.*?)\)", bt)
                for s in str_matches:
                    clean_s = s.replace("\\(", "(").replace("\\)", ")").strip()
                    if clean_s and not clean_s.startswith("/F") and not clean_s.startswith("Tj"):
                        extracted_chars += len(clean_s)
                        if "|" in clean_s or "\t" in clean_s or "table" in clean_s.lower():
                            has_grid = True

            for i in range(1, expected_page_count + 1):
                pages.append({
                    "page_number": i,
                    "width": 612.0,
                    "height": 792.0,
                    "char_count": extracted_chars,
                    "image_count": 0,
                    "has_table_grid": has_grid,
                })
            return pages
        except Exception:
            pass

        for i in range(1, expected_page_count + 1):
            pages.append({
                "page_number": i,
                "width": 612.0,
                "height": 792.0,
                "char_count": 0,
                "image_count": 0,
                "has_table_grid": False,
            })
        return pages
