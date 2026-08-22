from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.schemas.job import JobStatusResponse
from backend.services.job_service import job_service

router = APIRouter()


@router.get("/processing/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    job = job_service.get_job(db, job_id, tenant_id=tenant_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Processing job {job_id} not found.")

    return JobStatusResponse(
        job_id=job.id,
        product_id=job.product_id,
        status=job.status,
        step=job.step,
        progress=job.progress,
        result=job.result_json,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat() if job.updated_at else job.created_at.isoformat()
    )

