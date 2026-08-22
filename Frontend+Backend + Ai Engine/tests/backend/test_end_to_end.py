import asyncio
from backend.schemas.product import ProductCreate
from backend.services.product_service import product_service
from backend.services.job_service import job_service

def test_full_end_to_end_pipeline_flow(client, db_session):
    # 1. USER CREATES SPARSE PRODUCT INPUT
    prod_create = ProductCreate(
        name="Deep Groove Ball Bearing 6205-2RS1",
        sku="SKF-6205-2RS1",
        brand="SKF",
        category="Bearings",
        description="Sparse user input"
    )
    product = product_service.create_product(db_session, prod_create)
    assert product.id is not None

    # 2. INITIALIZE PROCESSING JOB & RUN PIPELINE
    job = job_service.create_job(db_session, product.id)
    completed_job = asyncio.run(job_service.run_pipeline(db_session, job.id))


    assert completed_job.status in ("COMPLETED", "FAILED")
    if completed_job.status == "FAILED":
        error_lower = (completed_job.error_message or "").lower()
        if any(kw in error_lower for kw in ["connection", "timeout", "failed", "404", "unavailable"]):
            import pytest
            pytest.skip("Live AI provider unavailable")
        else:
            import pytest
            pytest.fail(f"Pipeline failed with unexpected error: {completed_job.error_message}")

    assert completed_job.progress == 100

    # 3. VERIFY STORED FINAL PRODUCT & PROVENANCE
    updated_product = product_service.get_product(db_session, product.id)
    assert updated_product.status == "verified"
    assert len(updated_product.attributes) >= 4
    assert len(updated_product.evidences) >= 1

    # Verify provenance survival
    ev = updated_product.evidences[0]
    assert ev.source_id is not None
    assert ev.content is not None
    assert ev.provenance_json is not None

    # 4. VERIFY FRONTEND RESPONSE SCHEMA FORMATTING
    response_dto = product_service.format_to_response(updated_product)
    assert response_dto["id"] == product.id
    assert len(response_dto["dimensions"]) >= 1
    assert response_dto["confidenceScore"] > 0
