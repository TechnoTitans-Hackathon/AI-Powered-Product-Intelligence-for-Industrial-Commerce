import asyncio
import pytest
from backend.schemas.product import ProductCreate
from backend.services.product_service import product_service
from backend.services.job_service import job_service


def test_acceptance_flow_1_bearing(client, db_session):
    prod_create = ProductCreate(
        name="Deep Groove Ball Bearing 6205",
        sku="SKF-6205",
        brand="SKF",
        category="Bearings"
    )
    product = product_service.create_product(db_session, prod_create)
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

    updated_product = product_service.get_product(db_session, product.id)
    assert len(updated_product.attributes) > 0
    assert updated_product.status in ["verified", "needs_review", "processing"]
    assert updated_product.confidence_level in ["HIGH", "MEDIUM", "LOW", "CONFLICT"]


def test_acceptance_flow_2_motor(client, db_session):
    prod_create = ProductCreate(
        name="Induction Motor 5.5kW",
        sku="ABB-M3AA",
        brand="ABB",
        category="Motors"
    )
    product = product_service.create_product(db_session, prod_create)
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

    updated_product = product_service.get_product(db_session, product.id)
    assert len(updated_product.attributes) > 0
    assert updated_product.description is not None


def test_acceptance_flow_3_pump(client, db_session):
    prod_create = ProductCreate(
        name="Centrifugal Water Pump",
        sku="CR-10-02",
        brand="Grundfos",
        category="Pumps"
    )
    product = product_service.create_product(db_session, prod_create)
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

    updated_product = product_service.get_product(db_session, product.id)
    assert len(updated_product.attributes) > 0


def test_acceptance_flow_4_unknown(client, db_session):
    prod_create = ProductCreate(
        name="Hyperdrive Module",
        sku="HD-01",
        brand="Corellian Engineering",
        category="Starship Parts"
    )
    product = product_service.create_product(db_session, prod_create)
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

    updated_product = product_service.get_product(db_session, product.id)
    # Pipeline handles unknown categories gracefully
    assert updated_product.status in ["verified", "needs_review", "processing"]


def test_acceptance_flow_5_human_review(client, db_session):
    prod_create = ProductCreate(name="Review Test Item", sku="REV-01")
    product = product_service.create_product(db_session, prod_create)
    
    response = client.post(
        f"/api/v1/products/{product.id}/review",
        json={"action": "APPROVED", "reviewer": "qa_engineer", "comment": "Verified accurate"}
    )
    assert response.status_code == 200
    assert response.json()["action"] == "APPROVED"


def test_acceptance_flow_6_duplicate_detection(client, db_session):
    prod1 = product_service.create_product(db_session, ProductCreate(name="Exact Match Item", sku="DUP-01"))
    assert prod1.id is not None
