"""Analytics API endpoints — empirical data scoped to active tenant."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.db.models import Product, ProcessingJob, ValidationResult

router = APIRouter()


@router.get("/analytics/summary", response_model=Dict[str, Any])
def analytics_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Dashboard summary statistics — all values come from actual DB records for current tenant.
    No fake percentages or fabricated metrics.
    """
    # Product counts for tenant
    total_products = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id).scalar() or 0
    verified = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.status == "verified").scalar() or 0
    needs_review = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.status == "needs_review").scalar() or 0
    conflicting = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.status == "conflicting").scalar() or 0
    processing = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.status == "processing").scalar() or 0
    failed = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.status == "failed").scalar() or 0

    # Confidence distribution for tenant
    high_confidence = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.confidence_level == "HIGH").scalar() or 0
    medium_confidence = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.confidence_level == "MEDIUM").scalar() or 0
    low_confidence = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.confidence_level == "LOW").scalar() or 0
    conflict_confidence = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.confidence_level == "CONFLICT").scalar() or 0

    # Missing data for tenant
    products_with_missing = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.missing_fields_count > 0).scalar() or 0
    products_with_conflicts = db.query(func.count(Product.id)).filter(Product.tenant_id == tenant_id, Product.conflict_fields_count > 0).scalar() or 0

    # Validation issues for tenant
    unresolved_issues = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.resolved == False
    ).scalar() or 0

    # Job stats for tenant
    total_jobs = db.query(func.count(ProcessingJob.id)).filter(ProcessingJob.tenant_id == tenant_id).scalar() or 0
    completed_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "COMPLETED"
    ).scalar() or 0
    failed_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status == "FAILED"
    ).scalar() or 0
    in_progress_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.tenant_id == tenant_id,
        ProcessingJob.status.in_(["QUEUED", "PROCESSING"])
    ).scalar() or 0

    # Category distribution for tenant
    categories_raw = (
        db.query(Product.category, func.count(Product.id))
        .filter(Product.tenant_id == tenant_id)
        .group_by(Product.category)
        .all()
    )
    categories_dict = {cat or "General": cnt for cat, cnt in categories_raw}

    return {
        "products": {
            "total": total_products,
            "verified": verified,
            "needs_review": needs_review,
            "conflicting": conflicting,
            "processing": processing,
            "failed": failed,
            "with_missing_data": products_with_missing,
            "with_conflicts": products_with_conflicts,
        },
        "confidence_distribution": {
            "HIGH": high_confidence,
            "MEDIUM": medium_confidence,
            "LOW": low_confidence,
            "CONFLICT": conflict_confidence,
        },
        "validation": {
            "unresolved_issues": unresolved_issues,
            "needs_attention": needs_review + conflicting,
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "in_progress": in_progress_jobs,
            "success_rate": round(completed_jobs / total_jobs, 4) if total_jobs > 0 else 0,
        },
        "categories": categories_dict,
    }


@router.get("/analytics/recent-activity", response_model=List[Dict[str, Any]])
def recent_activity(
    limit: int = 20,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Recent platform activity — derived from real DB timestamps for the active tenant.
    Returns a unified timeline of meaningful events.
    """
    activities = []

    # Recent completed jobs for this tenant
    recent_jobs = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.tenant_id == tenant_id,
            ProcessingJob.status.in_(["COMPLETED", "FAILED"])
        )
        .order_by(ProcessingJob.updated_at.desc())
        .limit(limit)
        .all()
    )

    for job in recent_jobs:
        product = db.query(Product).filter(Product.id == job.product_id).first()
        if job.status == "COMPLETED":
            activities.append({
                "type": "processing_completed",
                "title": "Product processed successfully",
                "description": f"{product.name if product else 'Product'} intelligence generated",
                "product_id": job.product_id,
                "product_name": product.name if product else "Unknown",
                "timestamp": job.updated_at.isoformat() if job.updated_at else None,
                "status": "success",
            })
        else:
            activities.append({
                "type": "processing_failed",
                "title": "Processing failed",
                "description": f"{product.name if product else 'Product'}: {job.error_message or 'Unknown error'}",
                "product_id": job.product_id,
                "product_name": product.name if product else "Unknown",
                "timestamp": job.updated_at.isoformat() if job.updated_at else None,
                "status": "error",
            })

    # Sort by timestamp descending
    activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return activities[:limit]


@router.get("/analytics/recently-processed", response_model=List[Dict[str, Any]])
def recently_processed(
    limit: int = 10,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Products that recently completed processing for active tenant — for dashboard table."""
    jobs = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.tenant_id == tenant_id,
            ProcessingJob.status == "COMPLETED"
        )
        .order_by(ProcessingJob.updated_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for job in jobs:
        product = db.query(Product).filter(
            Product.id == job.product_id,
            Product.tenant_id == tenant_id
        ).first()
        if not product:
            continue
        results.append({
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku or product.mpn or "",
            "status": product.status,
            "confidence_level": product.confidence_level,
            "missing_fields": product.missing_fields_count or 0,
            "conflict_fields": product.conflict_fields_count or 0,
            "processed_at": job.updated_at.isoformat() if job.updated_at else None,
            "processing_time_ms": job.processing_time_ms,
        })
    return results


@router.get("/analytics/trends", response_model=Dict[str, Any])
def processing_trends(
    days: int = 7,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Processing trends over the last N days for active tenant.
    Only uses real job timestamps — no fabricated data.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    jobs = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.tenant_id == tenant_id,
            ProcessingJob.created_at >= cutoff
        )
        .all()
    )

    daily: dict[str, dict] = {}
    for job in jobs:
        if not job.created_at:
            continue
        day = job.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "completed": 0, "failed": 0}
        daily[day]["total"] += 1
        if job.status == "COMPLETED":
            daily[day]["completed"] += 1
        elif job.status == "FAILED":
            daily[day]["failed"] += 1

    return {
        "period_days": days,
        "daily_breakdown": sorted(daily.values(), key=lambda x: x["date"]),
        "total_processed": sum(d["total"] for d in daily.values()),
    }

