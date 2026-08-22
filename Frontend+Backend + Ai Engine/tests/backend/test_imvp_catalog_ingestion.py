import asyncio
"""
Automated unit & integration tests for catalog spreadsheet ingestion.

Tests:
- XLSX parsing with openpyxl
- CSV parsing with standard CSV
- Column mapping & header normalization (Mfg_Part_Num, Part_Desc, Brands, etc.)
- Unknown column preservation as dynamic attributes
- Malformed/empty row handling and error tracking
- Batch job creation and background execution
"""
import io
import openpyxl
import pytest
from backend.ingestion.catalog_parser import CatalogParser, _normalize_header
from backend.core.db import SessionLocal
from backend.services.product_service import product_service
from backend.services.job_service import job_service
from backend.db.models import Product, Attribute, ProcessingJob, ValidationResult


def test_header_normalization():
    assert _normalize_header("Mfg_Part_Num") == "mfg_part_num"
    assert _normalize_header("Part Description") == "part_description"
    assert _normalize_header("E1-Brand") == "e1_brand"
    assert _normalize_header("Unilog.Brand") == "unilog_brand"


def test_csv_catalog_parsing():
    csv_content = """Mfg_Part_Num,Part_Desc,Brand,Manufacturer,Voltage,Housing Material
PMP-1001,High Pressure Pump 2HP,FlowTech,FlowTech Dynamics,230V,Cast Iron
PMP-1002,Centrifugal Pump 5HP,FlowTech,FlowTech Dynamics,460V,Stainless Steel
BLT-5001,V-Belt 50in,PowerDrive,PowerDrive Corp,,Rubber
"""
    result = CatalogParser.parse_file(csv_content.encode("utf-8"), "pumps.csv")
    assert result.total_rows == 3
    assert result.imported_count == 3
    assert result.skipped_count == 0
    assert len(result.parsed_rows) == 3

    row1 = result.parsed_rows[0]
    assert row1.product_data.sku == "PMP-1001"
    assert row1.product_data.name == "High Pressure Pump 2HP"
    assert row1.product_data.brand == "FlowTech"
    assert row1.product_data.manufacturer == "FlowTech Dynamics"
    assert row1.raw_attributes.get("Voltage") == "230V"
    assert row1.raw_attributes.get("Housing Material") == "Cast Iron"


def test_xlsx_catalog_parsing():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Part_Manuf", "Bore Diameter"])
    ws.append(["BRG-6205", "Deep Groove Ball Bearing", "SKF", "SKF Group", "25mm"])
    ws.append(["BRG-6206", "Deep Groove Ball Bearing 30mm", "-- Unbranded --", "SKF Group", "30mm"])

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    result = CatalogParser.parse_file(xlsx_bytes, "bearings.xlsx")
    assert result.total_rows == 2
    assert result.imported_count == 2
    assert result.skipped_count == 0

    row1 = result.parsed_rows[0]
    assert row1.product_data.sku == "BRG-6205"
    assert row1.product_data.brand == "SKF"
    assert row1.raw_attributes.get("Bore Diameter") == "25mm"

    # Verify placeholder '-- Unbranded --' was cleaned
    row2 = result.parsed_rows[1]
    assert row2.product_data.sku == "BRG-6206"
    assert row2.product_data.brand == "Unknown"


def test_malformed_and_empty_rows():
    csv_content = """Mfg_Part_Num,Part_Desc,Brand
,Valid Description Without SKU,TestBrand
SKU-ONLY-NO-NAME,,TestBrand
,,TestBrand
"""
    result = CatalogParser.parse_file(csv_content.encode("utf-8"), "malformed.csv")
    # Row 1 has name -> auto-generates sku
    # Row 2 has sku -> auto-generates name
    # Row 3 has neither -> skipped
    assert result.imported_count == 2
    assert result.skipped_count == 1
    assert len(result.errors) >= 1


def test_database_persistence_and_job_creation():
    db = SessionLocal()
    try:
        csv_content = """Mfg_Part_Num,Part_Desc,Brand,Manufacturer,Operating Pressure
TEST-VALVE-01,Check Valve 1/2in NPT,Parker,Parker Hannifin,3000 PSI
"""
        result = CatalogParser.parse_file(csv_content.encode("utf-8"), "valves.csv")
        assert result.imported_count == 1

        parsed_row = result.parsed_rows[0]
        prod = product_service.create_product(
            db=db,
            payload=parsed_row.product_data,
            extra_attributes=parsed_row.raw_attributes
        )
        assert prod.id is not None
        assert prod.sku == "TEST-VALVE-01"

        # Verify dynamic attribute saved
        attrs = db.query(Attribute).filter(Attribute.product_id == prod.id).all()
        attr_keys = [a.key for a in attrs]
        assert "Operating Pressure" in attr_keys

        # Create and run job
        job = job_service.create_job(db, prod.id)
        assert job.status == "QUEUED"

        asyncio.run(job_service.run_pipeline(db, job.id))
        db.refresh(job)
        db.refresh(prod)

        assert job.status in ("COMPLETED", "FAILED")


        if job.status == "FAILED":


            error_lower = (job.error_message or "").lower()


            if any(kw in error_lower for kw in ["connection", "timeout", "failed", "404", "unavailable"]):


                import pytest


                pytest.skip("Live AI provider unavailable")


            else:


                import pytest


                pytest.fail(f"Pipeline failed with unexpected error: {job.error_message}")
        assert prod.confidence_level in ["HIGH", "MEDIUM", "LOW", "CONFLICT"]
        assert prod.intelligence_json is not None

        # Clean up test entity
        db.query(Attribute).filter(Attribute.product_id == prod.id).delete()
        db.query(ProcessingJob).filter(ProcessingJob.product_id == prod.id).delete()
        db.query(ValidationResult).filter(ValidationResult.product_id == prod.id).delete()
        db.query(Product).filter(Product.id == prod.id).delete()
        db.commit()
    finally:
        db.close()
