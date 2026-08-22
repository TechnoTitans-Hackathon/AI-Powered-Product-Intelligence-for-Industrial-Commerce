"""Commerce Output Adapter — maps internal AI model to expected commerce schema.

The 252-column expected output schema from `Unihack_ Expected Output.xlsx` is:
  MFR URL, Ref URL 1-5, PART_NUMBER, Dept, Class, Fine,
  SKU, Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf,
  MANUFACTURER_NAME, BRAND_NAME, TRADE_NAME, MANUFACTURER_PART_NUMBER,
  ALTERNATE_PART_NUMBER, Classpath, MOBILE_DESC, INVOICE_DESC,
  SHORT_DESC, LONG_DESC1, RETAIL_DESC, MARKETING_DESCRIPTION,
  ITEM_FEATURES_1..20, With, Standard/Approvals, Prop 65, Application,
  Includes, Product Name,
  ATTRIBUTE_LABEL/VALUE/UOM 1..50,
  UPC, EAN, GTIN, UNSPSC, Warranty, List Price, Selling Qty, Selling UOM,
  Standard Packaging Information, LENGTH, LENGTH_UOM, HEIGHT, HEIGHT_UOM,
  WIDTH, WIDTH_UOM, WEIGHT, WEIGHT_UOM, VOLUME, VOLUME_UOM,
  Product Image, Alternate Image 1-4,
  SDS, SDS_1, Warranty Information, Catalog, Specification Sheet,
  Instruction/Installation Manual, Service Manual, Owners/User Manual,
  Line Drawing, MTR, RoHS, Full Engineering Drawing, Energy Star Guide,
  Technical Bulletin, Submittal, Compatibility Chart, Size Chart,
  Product Label/Insert, Video Link, Video Link 1,
  Country Of Origin, Discontinued, Actual Image (Yes/No)

This adapter is DECOUPLED from the agents' internal reasoning model.
"""

from __future__ import annotations

import csv
import json
import io
import logging
from typing import Any, Optional

from ai_engine.schemas import FieldValue, ProductIntelligenceResult

logger = logging.getLogger(__name__)

# The exact column order from the expected output schema
COMMERCE_COLUMNS = [
    "MFR URL", "Ref URL 1", "Ref URL 2", "Ref URL 3", "Ref URL 4", "Ref URL 5",
    "PART_NUMBER", "Dept", "Class", "Fine",
    "SKU - MY_PART_NUMBER", "Mfg_Part_Num", "Part_Desc",
    "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
    "MANUFACTURER_NAME", "BRAND_NAME", "TRADE_NAME",
    "MANUFACTURER_PART_NUMBER", "ALTERNATE_PART_NUMBER",
    "Classpath", "MOBILE_DESC", "INVOICE_DESC",
    "SHORT_DESC", "LONG_DESC1", "RETAIL_DESC", "MARKETING_DESCRIPTION",
] + [f"ITEM_FEATURES_{i}" for i in range(1, 21)] + [
    "With", "Standard/Approvals", "Prop 65", "Application", "Includes", "Product Name",
] + [
    col
    for i in range(1, 51)
    for col in (f"ATTRIBUTE_LABEL {i}", f"ATTRIBUTE_VALUE {i}", f"ATTRIBUTE_UOM {i}")
] + [
    "UPC", "EAN", "GTIN", "UNSPSC",
    "Warranty", "List Price", "Selling Qty", "Selling UOM",
    "Standard Packaging Information",
    "LENGTH", "LENGTH_UOM", "HEIGHT", "HEIGHT_UOM",
    "WIDTH", "WIDTH_UOM", "WEIGHT", "WEIGHT_UOM", "VOLUME", "VOLUME_UOM",
    "Product Image", "Alternate Image 1", "Alternate Image 2",
    "Alternate Image 3", "Alternate Image 4",
    "SDS", "SDS_1", "Warranty Information", "Catalog", "Specification Sheet",
    "Instruction/Installation Manual", "Service Manual", "Owners/User Manual",
    "Line Drawing", "MTR", "RoHS", "Full Engineering Drawing",
    "Energy Star Guide", "Technical Bulletin", "Submittal",
    "Compatibility Chart", "Size Chart", "Product Label/Insert",
    "Video Link", "Video Link 1",
    "Country Of Origin", "Discontinued", "Actual Image (Yes/No)",
]


def _safe_value(fv: Optional[FieldValue]) -> str:
    """Extract display value from a FieldValue, or empty string."""
    if fv is None or fv.value is None:
        return ""
    return fv.display_value or fv.value or ""


class CommerceOutputAdapter:
    """Maps internal ProductIntelligenceResult → commerce-ready row.

    This is the ONLY place that knows about Excel column names.
    The AI reasoning never touches these names.
    """

    def adapt(self, result: ProductIntelligenceResult) -> dict[str, str]:
        """Convert a ProductIntelligenceResult to a commerce schema dict."""
        row: dict[str, str] = {col: "" for col in COMMERCE_COLUMNS}

        # Identity
        identity = result.identity
        input_data = result.product_input

        row["Mfg_Part_Num"] = identity.part_number or input_data.mfg_part_number or ""
        row["MANUFACTURER_PART_NUMBER"] = identity.part_number or ""
        row["ALTERNATE_PART_NUMBER"] = identity.alternate_part_number or ""
        row["Part_Desc"] = input_data.part_description or ""
        row["MANUFACTURER_NAME"] = identity.manufacturer_name_clean or identity.manufacturer or ""
        row["BRAND_NAME"] = identity.brand or ""
        row["TRADE_NAME"] = identity.trade_name or ""
        row["Part_Manuf"] = input_data.manufacturer or ""
        row["E1_Brand"] = input_data.brand or ""
        row["Unilog_Brand"] = input_data.unilog_brand or ""
        row["DIB_Brand"] = input_data.dib_brand or ""
        row["Product Name"] = identity.product_name or ""

        # Classification
        row["Dept"] = identity.department or ""
        row["Class"] = identity.product_class or ""
        row["Fine"] = identity.fine_class or ""
        row["Classpath"] = identity.classpath or ""

        # Descriptions
        row["SHORT_DESC"] = _safe_value(result.short_description)
        row["LONG_DESC1"] = _safe_value(result.long_description)
        row["MARKETING_DESCRIPTION"] = _safe_value(result.marketing_description)
        row["RETAIL_DESC"] = _safe_value(result.retail_description)
        row["MOBILE_DESC"] = _safe_value(result.mobile_description)
        row["INVOICE_DESC"] = _safe_value(result.invoice_description)

        # Features (up to 20)
        for i, feat in enumerate(result.features[:20]):
            row[f"ITEM_FEATURES_{i + 1}"] = _safe_value(feat) if isinstance(feat, FieldValue) else str(feat)

        # Applications, standards, etc.
        row["Application"] = _safe_value(result.applications)
        row["Standard/Approvals"] = _safe_value(result.standards_approvals)
        row["With"] = _safe_value(result.with_info)
        row["Prop 65"] = _safe_value(result.prop_65)
        row["Includes"] = _safe_value(result.includes)

        # Attributes (up to 50 triplets)
        for i, attr in enumerate(result.attributes[:50]):
            idx = i + 1
            row[f"ATTRIBUTE_LABEL {idx}"] = attr.field_name or ""
            row[f"ATTRIBUTE_VALUE {idx}"] = attr.value or ""
            row[f"ATTRIBUTE_UOM {idx}"] = attr.unit or ""

        # Identifiers
        row["UPC"] = _safe_value(result.upc)
        row["EAN"] = _safe_value(result.ean)
        row["GTIN"] = _safe_value(result.gtin)
        row["UNSPSC"] = _safe_value(result.unspsc)

        # Commercial
        row["Warranty"] = _safe_value(result.warranty)
        row["List Price"] = _safe_value(result.list_price)
        row["Selling Qty"] = _safe_value(result.selling_qty)
        row["Selling UOM"] = _safe_value(result.selling_uom)
        row["Country Of Origin"] = _safe_value(result.country_of_origin)
        row["Discontinued"] = _safe_value(result.discontinued)

        # Dimensions
        for dim_key, col, uom_col in [
            ("length", "LENGTH", "LENGTH_UOM"),
            ("height", "HEIGHT", "HEIGHT_UOM"),
            ("width", "WIDTH", "WIDTH_UOM"),
            ("weight", "WEIGHT", "WEIGHT_UOM"),
            ("volume", "VOLUME", "VOLUME_UOM"),
        ]:
            dim = result.dimensions.get(dim_key)
            if dim:
                row[col] = dim.value or ""
                row[uom_col] = dim.unit or ""

        # URLs
        row["MFR URL"] = _safe_value(result.mfr_url)
        for i, ref_url in enumerate(result.reference_urls[:5]):
            row[f"Ref URL {i + 1}"] = _safe_value(ref_url)

        # Images
        for i, img in enumerate(result.images[:5]):
            if i == 0:
                row["Product Image"] = _safe_value(img)
            else:
                row[f"Alternate Image {i}"] = _safe_value(img)

        return row

    def adapt_batch(self, results: list[ProductIntelligenceResult]) -> list[dict[str, str]]:
        """Convert a batch of results to commerce rows."""
        return [self.adapt(r) for r in results]

    def to_csv(self, results: list[ProductIntelligenceResult]) -> str:
        """Export batch results as CSV string."""
        rows = self.adapt_batch(results)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=COMMERCE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue()

    def to_json(self, result: ProductIntelligenceResult) -> str:
        """Export a single result as JSON with full intelligence metadata."""
        commerce_row = self.adapt(result)
        output = {
            "commerce_data": commerce_row,
            "intelligence_metadata": {
                "request_id": result.request_id,
                "processing_status": result.processing_status.value,
                "overall_confidence": result.overall_confidence,
                "completeness_ratio": result.completeness_ratio,
                "fields_total": result.fields_total,
                "fields_populated": result.fields_populated,
                "fields_missing": result.fields_missing,
                "fields_conflicting": result.fields_conflicting,
                "fields_needing_review": result.fields_needing_review,
                "conflicts": [c.model_dump() for c in result.conflicts],
                "enrichment_version": result.enrichment_version,
                "created_at": result.created_at.isoformat(),
            },
        }
        return json.dumps(output, indent=2, default=str)

    @staticmethod
    def get_columns() -> list[str]:
        """Return the commerce column list for reference."""
        return COMMERCE_COLUMNS.copy()
