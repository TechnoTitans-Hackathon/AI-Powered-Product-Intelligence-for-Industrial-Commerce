"""Validation Center API endpoints — scoped to active tenant."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.db.models import ValidationResult, Product
from backend.core.logging import logger

router = APIRouter()


def _format_issue(issue: ValidationResult, product_name: str = "") -> Dict[str, Any]:
    return {
        "id": issue.id,
        "product_id": issue.product_id,
        "product_name": product_name,
        "severity": issue.severity,
        "type": issue.type,
        "field": issue.field,
        "message": issue.message,
        "current_value": issue.current_value,
        "suggested_value": issue.suggested_value,
        "source_a": issue.source_a,
        "source_b": issue.source_b,
        "resolved": issue.resolved,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }


@router.get("/validation", response_model=List[Dict[str, Any]])
def list_validation_issues(
    product_id: Optional[str] = None,
    severity: Optional[str] = None,
    type: Optional[str] = None,
    resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """List validation issues with optional filters scoped to current tenant."""
    query = db.query(ValidationResult).filter(ValidationResult.tenant_id == tenant_id)
    if product_id:
        query = query.filter(ValidationResult.product_id == product_id)
    if severity:
        query = query.filter(ValidationResult.severity == severity)
    if type:
        query = query.filter(ValidationResult.type == type)
    if resolved is not None:
        query = query.filter(ValidationResult.resolved == resolved)

    issues = query.order_by(ValidationResult.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for issue in issues:
        product = db.query(Product).filter(Product.id == issue.product_id, Product.tenant_id == tenant_id).first()
        result.append(_format_issue(issue, product.name if product else ""))
    return result


@router.get("/validation/summary", response_model=Dict[str, Any])
def validation_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Get overall validation statistics for current tenant."""
    from sqlalchemy import func

    total = db.query(func.count(ValidationResult.id)).filter(ValidationResult.tenant_id == tenant_id).scalar() or 0
    resolved = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.resolved == True
    ).scalar() or 0
    conflicts = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.type == "conflict"
    ).scalar() or 0
    missing = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.type == "missing_field"
    ).scalar() or 0
    critical = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.severity == "critical"
    ).scalar() or 0
    high = db.query(func.count(ValidationResult.id)).filter(
        ValidationResult.tenant_id == tenant_id,
        ValidationResult.severity == "high"
    ).scalar() or 0

    return {
        "total_issues": total,
        "resolved": resolved,
        "unresolved": total - resolved,
        "conflicts": conflicts,
        "missing_fields": missing,
        "critical": critical,
        "high": high,
        "needs_attention": critical + high,
    }


@router.post("/validation/{issue_id}/resolve", response_model=Dict[str, Any])
def resolve_issue(
    issue_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Resolve a validation issue, optionally providing a corrected value.
    """
    issue = db.query(ValidationResult).filter(
        ValidationResult.id == issue_id,
        ValidationResult.tenant_id == tenant_id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail=f"Validation issue {issue_id} not found.")

    issue.resolved = payload.get("resolved", True)
    if payload.get("corrected_value"):
        issue.current_value = payload["corrected_value"]
    db.commit()
    db.refresh(issue)
    logger.info(f"Validation issue {issue_id} resolved by {payload.get('reviewer', 'user')}")

    product = db.query(Product).filter(Product.id == issue.product_id, Product.tenant_id == tenant_id).first()
    return _format_issue(issue, product.name if product else "")

