import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.ingestion.pdf.schemas import PDFTable, BoundingBox, PDFPageNode


class PDFTableExtractor:
    """
    Table Extraction Engine.
    Detects tables, extracts structured JSON tables with columns/rows/units/headers,
    and generates LLM-ready markdown textual representations.
    """

    def extract_tables_from_pages(self, file_path: Path, page_nodes: List[PDFPageNode]) -> List[PDFTable]:
        """
        Extracts structured tables across all document page nodes.
        """
        all_tables: List[PDFTable] = []

        for page_node in page_nodes:
            tables_on_page = self._extract_tables_for_page(file_path, page_node)
            page_node.tables = tables_on_page
            all_tables.extend(tables_on_page)

        return all_tables

    def _extract_tables_for_page(self, file_path: Path, page_node: PDFPageNode) -> List[PDFTable]:
        """Attempts table extraction using pdfplumber/fitz or text block pipe matrix parser."""
        tables: List[PDFTable] = []
        page_number = page_node.page_number

        # 1. Try pdfplumber for accurate cell grid & unit parsing
        try:
            import pdfplumber
            with pdfplumber.open(str(file_path)) as pdf:
                if page_number <= len(pdf.pages):
                    page = pdf.pages[page_number - 1]
                    extracted_tables = page.extract_tables()
                    for idx, table_data in enumerate(extracted_tables):
                        if not table_data or len(table_data) < 2:
                            continue

                        parsed_table = self._build_table_from_matrix(
                            table_matrix=table_data,
                            page_number=page_number,
                            table_idx=idx + 1,
                        )
                        if parsed_table:
                            tables.append(parsed_table)

                    if tables:
                        return tables
        except Exception:
            pass

        # 2. Try fitz (PyMuPDF) table extraction feature
        try:
            import fitz
            doc = fitz.open(str(file_path))
            page = doc[page_number - 1]
            tabs = page.find_tables()
            doc.close()

            for idx, tab in enumerate(tabs, start=1):
                matrix = tab.extract()
                bbox_tuple = tab.bbox
                parsed_table = self._build_table_from_matrix(
                    table_matrix=matrix,
                    page_number=page_number,
                    table_idx=idx,
                    bbox_coords=bbox_tuple,
                )
                if parsed_table:
                    tables.append(parsed_table)

            if tables:
                return tables
        except Exception:
            pass

        # 3. Parse pipe '|' delimited text lines inside page_node text blocks as structured PDFTable
        pipe_matrix = []
        for blk in page_node.text_blocks:
            for line in blk.text.split("\n"):
                if "|" in line:
                    row_cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(row_cells) >= 2:
                        pipe_matrix.append(row_cells)

        if pipe_matrix and len(pipe_matrix) >= 2:
            parsed_table = self._build_table_from_matrix(
                table_matrix=pipe_matrix,
                page_number=page_number,
                table_idx=1,
                title=f"Table (Page {page_number})",
            )
            if parsed_table:
                tables.append(parsed_table)

        return tables

    def _build_table_from_matrix(
        self,
        table_matrix: List[List[Optional[str]]],
        page_number: int,
        table_idx: int,
        bbox_coords: Optional[Tuple[float, float, float, float]] = None,
        title: Optional[str] = None,
    ) -> Optional[PDFTable]:
        """
        Parses a 2D matrix of raw cell strings into a canonical PDFTable structure.
        Dynamically extracts columns, row headers, cell values, and measurement units without hardcoding.
        """
        clean_matrix = []
        for row in table_matrix:
            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
            if any(clean_row):
                clean_matrix.append(clean_row)

        if not clean_matrix or len(clean_matrix) < 2:
            return None

        raw_headers = clean_matrix[0]
        columns = [h if h else f"Column_{i+1}" for i, h in enumerate(raw_headers)]

        rows: List[Dict[str, Any]] = []
        row_headers: List[str] = []
        units: Dict[str, str] = {}

        for col_name in columns:
            unit_match = re.search(r"[\(\[\{]([^\)\]\}]+)[\)\]\}]", col_name)
            if unit_match:
                units[col_name] = unit_match.group(1).strip()

        for row_data in clean_matrix[1:]:
            row_dict: Dict[str, Any] = {}
            row_header_val = row_data[0] if row_data else ""
            if row_header_val:
                row_headers.append(row_header_val)

            for col_idx, col_name in enumerate(columns):
                val_str = row_data[col_idx] if col_idx < len(row_data) else ""
                row_dict[col_name] = val_str

                if col_name not in units and val_str:
                    val_unit_match = re.search(r"\d+\s*([a-zA-Z°℃℉/%]+(?:\s*[a-zA-Z]+)?)$", val_str)
                    if val_unit_match and len(val_unit_match.group(1)) <= 10:
                        units[col_name] = val_unit_match.group(1).strip()

            rows.append(row_dict)

        table_title = title or f"Table {table_idx} (Page {page_number})"
        table_id = f"tbl_p{page_number}_{uuid.uuid4().hex[:6]}"

        text_rep = self.generate_table_text_representation(
            title=table_title,
            page_number=page_number,
            columns=columns,
            rows=rows,
        )

        bbox_obj = None
        if bbox_coords:
            bbox_obj = BoundingBox(
                x0=float(bbox_coords[0]),
                y0=float(bbox_coords[1]),
                x1=float(bbox_coords[2]),
                y1=float(bbox_coords[3]),
            )

        return PDFTable(
            table_id=table_id,
            page_number=page_number,
            title=table_title,
            columns=columns,
            rows=rows,
            row_headers=row_headers if row_headers else None,
            units=units,
            bbox=bbox_obj,
            text_representation=text_rep,
        )

    def generate_table_text_representation(
        self, title: str, page_number: int, columns: List[str], rows: List[Dict[str, Any]]
    ) -> str:
        """
        Generates LLM-ready markdown formatted text representation of the table.
        """
        lines = [
            f"TABLE: {title}",
            f"Page: {page_number}",
            "",
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join(["---"] * len(columns)) + " |",
        ]

        for r in rows:
            row_str = "| " + " | ".join([str(r.get(c, "")).replace("\n", " ") for c in columns]) + " |"
            lines.append(row_str)

        lines.append("")
        return "\n".join(lines)
