import os
import pytest
import asyncio
import cv2
import numpy as np
from backend.schemas.product import ProductCreate
from backend.services.product_service import product_service
from backend.services.job_service import job_service

@pytest.fixture(scope="session")
def dummy_video():
    path = "tests/backend/dummy_test_video.mp4"
    if not os.path.exists(path):
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 1.0, (100, 100))
        for _ in range(3):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[:] = (0, 255, 0)
            out.write(frame)
        out.release()
    return path

@pytest.mark.asyncio
async def test_imvp_video_analysis(client, db_session, dummy_video):
    prod_create = ProductCreate(
        name="Test Video Product",
        sku="VID-01",
        category="Industrial",
    )
    product = product_service.create_product(db_session, prod_create)
    
    with open(dummy_video, "rb") as f:
        response = client.post(
            "/api/v1/uploads",
            data={"product_id": product.id},
            files={"file": ("dummy_test_video.mp4", f, "video/mp4")}
        )
    
    assert response.status_code == 201
    assert response.json()["file_type"] == "video"
    
    job = job_service.create_job(db_session, product.id)
    completed_job = await job_service.run_pipeline(db_session, job.id)
    
    assert completed_job.status in ("COMPLETED", "FAILED")
    if completed_job.status == "FAILED":
        if "connection" in (completed_job.error_message or "").lower() or "timeout" in (completed_job.error_message or "").lower() or "all connection attempts failed" in (completed_job.error_message or "").lower() or "provider" in (completed_job.error_message or "").lower() or "unavailable" in (completed_job.error_message or "").lower():
            pytest.skip("Live AI provider unavailable")
        else:
            pytest.fail(f"Pipeline failed with unexpected error: {completed_job.error_message}")
            
    updated_product = product_service.get_product(db_session, product.id)
    assert len(updated_product.attributes) > 0 or updated_product.description is not None
