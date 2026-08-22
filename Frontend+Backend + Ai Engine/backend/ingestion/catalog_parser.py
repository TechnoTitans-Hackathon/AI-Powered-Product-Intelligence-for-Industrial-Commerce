"""
Catalog Parser — parses batch CSV and XLSX industrial product spreadsheets.

Features:
- Handles openpyxl (XLSX/XLS) and standard CSV with encoding detection.
- Column normalization layer mapping diverse header aliases to canonical fields.
- Filters out placeholder values (e.g. '-- Unbranded --', '-- No Unilog Brand --').
- Preserves all unmapped / extra columns as dynamic attributes.
- Graceful malformed/empty row handling with error reporting.
"""
from __future__ import annotations

import io
import os
import csv
import openpyxl
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from backend.schemas.product import ProductCreate
from backend.core.logging import logger


class ParsedRow(BaseModel):
    product_data: ProductCreate
    raw_attributes: Dict[str, Any]
    row_number: int


class CatalogParseResult(BaseModel):
    total_rows: int
    imported_count: int
    skipped_count: int
    parsed_rows: List[ParsedRow]
    errors: List[str]
    headers_detected: List[str]


# ─── Canonical Column Aliases ──────────────────────────────────────────────────

COLUMN_ALIASES: Dict[str, List[str]] = {
    "sku": [
        "mfg_part_num", "mfg_part_no", "mfgpartnum", "part_number", "part_no", "partnum",
        "sku", "mpn", "item_number", "item_no", "item_num", "material_number",
        "product_code", "catalog_number", "cat_no", "model_number", "model_no"
    ],
    "name": [
        "part_desc", "part_description", "product_name", "item_name", "name",
        "description", "product_description", "title", "item_desc", "short_desc"
    ],
    "brand": [
        "brand", "brand_name", "unilog_brand", "e1_brand", "dib_brand",
        "manufacturer_brand", "mfg_brand"
    ],
    "manufacturer": [
        "part_manuf", "manufacturer", "mfg", "maker", "vendor", "manufacturer_name",
        "mfg_name", "supplier"
    ],
    "category": [
        "category", "taxonomy", "product_category", "cat_name", "group",
        "product_group", "item_category", "segment"
    ],
    "subcategory": [
        "subcategory", "sub_category", "sub_cat", "sub_group"
    ],
    "industry": [
        "industry", "sector", "market", "application_industry"
    ],
    "description": [
        "long_desc", "long_description", "details", "extended_description",
        "technical_description", "specs_summary"
    ],
}

PLACEHOLDER_VALUES = {
    "-- unbranded --", "-- no unilog brand --", "-- no dib brand --",
    "unbranded", "no brand", "n/a", "na", "null", "none", "unknown",
    "-", "--", "undefined"
}


def _clean_str(val: Any) -> Optional[str]:
    """Clean string values and strip whitespace; return None for empty or placeholders."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.lower() in PLACEHOLDER_VALUES:
        return None
    return s


def _normalize_header(header: str) -> str:
    """Normalize a header string to lowercase alphanumeric with underscores."""
    if not header:
        return ""
    h = str(header).strip().lower()
    h = h.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
    return "".join(c for c in h if c.isalnum() or c == "_")


class CatalogParser:
    """Parses Excel and CSV files into canonical ProductCreate models and dynamic attributes."""

    @staticmethod
    def parse_file(content_bytes: bytes, filename: str) -> CatalogParseResult:
        ext = os.path.splitext(filename)[1].lower()

        if ext in [".xlsx", ".xls"]:
            return CatalogParser._parse_xlsx(content_bytes, filename)
        elif ext in [".csv", ".tsv", ".txt"]:
            return CatalogParser._parse_csv(content_bytes, filename)
        else:
            raise ValueError(f"Unsupported catalog file format '{ext}'. Must be .xlsx, .xls, or .csv")

    @staticmethod
    def _parse_xlsx(content_bytes: bytes, filename: str) -> CatalogParseResult:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True, read_only=True)
            ws = wb.active
        except Exception as e:
            logger.error(f"Failed to open Excel workbook {filename}: {e}")
            return CatalogParseResult(
                total_rows=0, imported_count=0, skipped_count=0,
                parsed_rows=[], errors=[f"Corrupt or unreadable Excel file: {str(e)}"],
                headers_detected=[]
            )

        rows_iter = ws.iter_rows(values_only=True)
        try:
            raw_headers = next(rows_iter, None)
        except Exception as e:
            return CatalogParseResult(
                total_rows=0, imported_count=0, skipped_count=0,
                parsed_rows=[], errors=["Empty Excel spreadsheet"],
                headers_detected=[]
            )

        if not raw_headers:
            return CatalogParseResult(
                total_rows=0, imported_count=0, skipped_count=0,
                parsed_rows=[], errors=["Empty Excel spreadsheet (no headers found)"],
                headers_detected=[]
            )

        headers = [_normalize_header(h) if h else f"col_{i}" for i, h in enumerate(raw_headers)]
        original_headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_headers)]

        return CatalogParser._process_rows(rows_iter, headers, original_headers, filename)

    @staticmethod
    def _parse_csv(content_bytes: bytes, filename: str) -> CatalogParseResult:
        # Try UTF-8 first, fallback to Latin-1
        text = None
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = content_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            text = content_bytes.decode("utf-8", errors="ignore")

        f = io.StringIO(text)
        reader = csv.reader(f)
        try:
            raw_headers = next(reader, None)
        except Exception as e:
            return CatalogParseResult(
                total_rows=0, imported_count=0, skipped_count=0,
                parsed_rows=[], errors=[f"Could not read CSV: {str(e)}"],
                headers_detected=[]
            )

        if not raw_headers:
            return CatalogParseResult(
                total_rows=0, imported_count=0, skipped_count=0,
                parsed_rows=[], errors=["Empty CSV file (no headers found)"],
                headers_detected=[]
            )

        headers = [_normalize_header(h) if h else f"col_{i}" for i, h in enumerate(raw_headers)]
        original_headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_headers)]

        return CatalogParser._process_rows(reader, headers, original_headers, filename)

    @staticmethod
    def _process_rows(
        rows_iter: Any,
        headers: List[str],
        original_headers: List[str],
        filename: str
    ) -> CatalogParseResult:
        parsed_rows: List[ParsedRow] = []
        errors: List[str] = []
        total_rows = 0
        imported_count = 0
        skipped_count = 0

        # Build column index mapping
        col_map = CatalogParser._build_column_mapping(headers)

        for row_idx, raw_row in enumerate(rows_iter, start=2):
            if raw_row is None:
                continue

            # Convert row tuple/list to dict
            row_dict = {}
            has_data = False
            for idx, val in enumerate(raw_row):
                if idx < len(headers):
                    cleaned = _clean_str(val)
                    if cleaned:
                        has_data = True
                    row_dict[headers[idx]] = cleaned

            if not has_data:
                # Skip entirely blank rows
                continue

            total_rows += 1

            # Extract fields
            extracted = CatalogParser._map_row_fields(row_dict, col_map, row_idx)
            if not extracted:
                skipped_count += 1
                errors.append(f"Row {row_idx}: Missing both part number and product name; skipped.")
                continue

            prod_create, extra_attrs = extracted
            parsed_rows.append(ParsedRow(
                product_data=prod_create,
                raw_attributes=extra_attrs,
                row_number=row_idx
            ))
            imported_count += 1

        return CatalogParseResult(
            total_rows=total_rows,
            imported_count=imported_count,
            skipped_count=skipped_count,
            parsed_rows=parsed_rows,
            errors=errors,
            headers_detected=original_headers
        )

    @staticmethod
    def _build_column_mapping(headers: List[str]) -> Dict[str, List[str]]:
        """Map canonical field names to the actual header names found in the spreadsheet."""
        mapping: Dict[str, List[str]] = {k: [] for k in COLUMN_ALIASES}
        assigned_headers = set()

        # Phase 1: Exact matches
        for h in headers:
            for canonical, aliases in COLUMN_ALIASES.items():
                if h in aliases:
                    if h not in mapping[canonical]:
                        mapping[canonical].append(h)
                        assigned_headers.add(h)
                    break

        # Phase 2: Word-based containment for unassigned headers
        for h in headers:
            if h in assigned_headers:
                continue
            for canonical, aliases in COLUMN_ALIASES.items():
                matched = False
                for alias in aliases:
                    words = h.split("_")
                    if alias in words or alias.replace("_", "") in words:
                        mapping[canonical].append(h)
                        assigned_headers.add(h)
                        matched = True
                        break
                if matched:
                    break

        return mapping

    @staticmethod
    def _map_row_fields(
        row_dict: Dict[str, Any],
        col_map: Dict[str, List[str]],
        row_idx: int
    ) -> Optional[Tuple[ProductCreate, Dict[str, Any]]]:
        def _get_first(canonical_key: str) -> Optional[str]:
            for h in col_map.get(canonical_key, []):
                val = row_dict.get(h)
                if val:
                    return val
            return None

        # 1. Part Number / SKU
        sku = _get_first("sku")

        # 2. Name / Description
        name = _get_first("name")
        desc = _get_first("description")

        # If name is missing but sku is present, or vice versa
        if not name and not sku:
            return None

        if not name:
            name = f"Product {sku}"
        if not sku:
            sku = f"ITEM-{row_idx:04d}"

        # 3. Brand (supports fallback across multiple brand columns e.g. E1_Brand, Unilog_Brand, DIB_Brand)
        brand = _get_first("brand")

        # 4. Manufacturer
        manufacturer = _get_first("manufacturer")

        # 5. Category & Subcategory
        category = _get_first("category") or "Industrial Equipment"
        subcategory = _get_first("subcategory")
        industry = _get_first("industry") or "Industrial Manufacturing"

        # 6. Preserve all other unmapped non-empty columns as dynamic attributes
        used_headers = set()
        for header_list in col_map.values():
            used_headers.update(header_list)

        extra_attrs: Dict[str, Any] = {}
        for h, val in row_dict.items():
            if h not in used_headers and val is not None:
                display_key = h.replace("_", " ").title()
                extra_attrs[display_key] = val

        prod_create = ProductCreate(
            name=name,
            sku=sku,
            mpn=sku,
            brand=brand or "Unknown",
            manufacturer=manufacturer or "Unknown",
            category=category,
            subcategory=subcategory or "",
            industry=industry,
            description=desc or f"{name}. Part Number: {sku}",
        )

        return prod_create, extra_attrs
