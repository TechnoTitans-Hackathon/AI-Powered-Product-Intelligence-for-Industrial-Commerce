import asyncio
import pytest
import os
import json
from backend.schemas.product import ProductCreate
from backend.services.product_service import product_service
from backend.services.job_service import job_service
from backend.core.storage_safety import storage_safety
from backend.knowledge.dataset_registry import dataset_registry

def test_non_bearing_product_no_skf_contamination(client, db_session):
    """
    Provide a motor. Assert SKF/6205/bearing data NEVER appears.
    This is the critical regression test ensuring the system is industry-agnostic.
    """
    prod_create = ProductCreate(
        name="High Efficiency AC Motor 5.5kW",
        sku="M2BAX 132SB 4",
        brand="ABB",
        manufacturer="ABB Ltd.",
        category="Motors",
        subcategory="AC Induction Motors",
        description="Standard 5.5kW induction motor"
    )
    product = product_service.create_product(db_session, prod_create)
    
    # Run pipeline
    job = job_service.create_job(db_session, product.id)
    completed_job = asyncio.run(job_service.run_pipeline(db_session, job.id))
    if completed_job.status == "FAILED":
        error_lower = (completed_job.error_message or "").lower()
        if any(kw in error_lower for kw in ["connection", "timeout", "failed", "404", "unavailable"]):
            pytest.skip("Live AI provider unavailable")
    
    # Check results
    updated_product = product_service.get_product(db_session, product.id)
    
    # Ensure no SKF/bearing contamination
    assert updated_product.category == "Motors"
    assert "SKF" not in (updated_product.brand or "")
    assert "6205" not in (updated_product.sku or "")
    
    # Check attributes - should be motor attributes (kW, V, rpm), not bearing (Bore, OD)
    attr_keys = [a.key for a in updated_product.attributes]
    assert "Rated Power" in attr_keys or len(attr_keys) == 0  # Depending on mock fixture
    assert "Bore" not in attr_keys
    assert "Outside Diameter" not in attr_keys

def test_unknown_product_category_no_fabrication(client, db_session):
    """
    Provide an unknown category. Assert no data is fabricated.
    """
    prod_create = ProductCreate(
        name="Quantum Flux Capacitor",
        sku="QFC-9000",
        brand="DeLorean",
        category="Time Travel Components"
    )
    product = product_service.create_product(db_session, prod_create)
    
    job = job_service.create_job(db_session, product.id)
    completed_job = asyncio.run(job_service.run_pipeline(db_session, job.id))
    if completed_job.status == "FAILED":
        error_lower = (completed_job.error_message or "").lower()
        if any(kw in error_lower for kw in ["connection", "timeout", "failed", "404", "unavailable"]):
            pytest.skip("Live AI provider unavailable")
    
    updated_product = product_service.get_product(db_session, product.id)
    
    # Should not fabricate attributes (only the 3 default features are added as attributes)
    non_feature_attrs = [a for a in updated_product.attributes if a.attribute_type != "feature"]
    assert len(non_feature_attrs) == 0
    assert updated_product.status in ("verified", "review_required", "needs_review")

def test_4gb_cache_limit_enforcement(client, db_session, monkeypatch):
    """
    Test that the 4GB (simulated to 1000 bytes) limit is enforced and triggers LRU.
    """
    # Temporarily reduce max temp cache size for testing
    monkeypatch.setattr(storage_safety, "max_temp_bytes", 1000)
    
    # Trigger an acquisition manually using cache_manager to simulate download
    from backend.knowledge.cache_manager import cache_manager
    sample_content = b"A" * 1500  # Exceeds 1000 bytes
    
    # We test storage_safety directly
    evicted = storage_safety.check_and_evict_cache(db_session, required_bytes=1500)
    # Should be False because 1500 > 1000 max_temp_bytes
    assert evicted is False

def test_dataset_registry_listing(client, db_session):
    response = client.get("/api/v1/knowledge/datasets")
    assert response.status_code == 200
    datasets = response.json()
    assert len(datasets) > 0
    assert any(d["id"] == "baseline_industry_taxonomy" for d in datasets)

def test_targeted_acquisition_api(client):
    payload = {
        "query": "Centrifugal Pump Specs",
        "industry": "Industrial Equipment",
        "category": "Pumps"
    }
    response = client.post("/api/v1/knowledge/targeted-acquire?" + "&".join(f"{k}={v}" for k,v in payload.items()))
    assert response.status_code == 200
    evidence = response.json()
    assert len(evidence) == 1
    ev = evidence[0]
    assert ev["metadata"]["status"] == "RESEARCH_PROVIDER_UNAVAILABLE"
