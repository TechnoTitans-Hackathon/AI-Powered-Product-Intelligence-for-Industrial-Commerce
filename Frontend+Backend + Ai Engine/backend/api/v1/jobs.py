"""Jobs / Batch Processing API endpoints — scoped to active tenant."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.db.models import ProcessingJob, Product
from backend.services.job_service import job_service
from backend.core.logging import logger

router = APIRouter()


def _format_job(job: ProcessingJob) -> Dict[str, Any]:
    """Format a ProcessingJob into a clean API response dict."""
    return {
        "id": job.id,
        "product_id": job.product_id,
        "tenant_id": job.tenant_id,
        "status": job.status,
        "step": job.step,
        "pipeline_stage": job.pipeline_stage,
        "progress": job.progress,
        "processing_time_ms": job.processing_time_ms,
        "error_message": job.error_message,
        "result": job.result_json,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.get("/jobs", response_model=List[Dict[str, Any]])
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """List processing jobs for current tenant with optional status filter."""
    jobs = job_service.list_jobs(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        tenant_id=tenant_id
    )
    return [_format_job(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Get a specific processing job by ID for current tenant."""
    job = job_service.get_job(db, job_id, tenant_id=tenant_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return _format_job(job)


@router.post("/batch", response_model=Dict[str, Any], status_code=202)
def submit_batch(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Submit a batch of product IDs for processing.
    """
    product_ids = payload.get("product_ids", [])
    if not product_ids:
        raise HTTPException(status_code=400, detail="No product_ids provided.")

    ai_mode_str = payload.get("ai_mode", "AUTO")
    try:
        from backend.schemas.ai_contract import AIProcessingMode
        ai_mode = AIProcessingMode(ai_mode_str)
    except ValueError:
        ai_mode = AIProcessingMode.AUTO

    created_jobs = []
    for product_id in product_ids:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == tenant_id
        ).first()
        if not product:
            logger.warning(f"Batch: product {product_id} not found for tenant {tenant_id}, skipping.")
            continue
        job = job_service.create_job(db, product_id, tenant_id=tenant_id, ai_mode=ai_mode)
        background_tasks.add_task(_run_job_background, job.id)
        created_jobs.append(job.id)

    return {
        "message": f"Batch submitted: {len(created_jobs)} jobs created.",
        "job_ids": created_jobs,
        "total": len(created_jobs),
    }


@router.get("/batch/summary", response_model=Dict[str, Any])
def batch_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Get batch processing summary statistics for active tenant."""
    total = db.query(func.count(ProcessingJob.id)).filter(ProcessingJob.tenant_id == tenant_id).scalar() or 0
    completed = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "COMPLETED"
    ).scalar() or 0
    failed = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "FAILED"
    ).scalar() or 0
    processing = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "PROCESSING"
    ).scalar() or 0
    queued = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "QUEUED"
    ).scalar() or 0

    return {
        "total_jobs": total,
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "queued": queued,
        "remaining": queued + processing,
    }


def _run_job_background(job_id: str):
    """Background task wrapper for job execution."""
    import asyncio
    from backend.core.db import SessionLocal
    db = SessionLocal()
    try:
        asyncio.run(job_service.run_pipeline(db, job_id))
    finally:
        db.close()

