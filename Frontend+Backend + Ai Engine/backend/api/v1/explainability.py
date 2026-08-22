"""Explainability / Source Evidence API endpoints — scoped to active tenant."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.db.models import Product, Evidence, SourceDocument

router = APIRouter()


@router.get("/explainability/{product_id}", response_model=Dict[str, Any])
def get_product_explainability(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Get full explainability data for a product — sources, evidence, field support.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    # Evidence snippets
    evidences = db.query(Evidence).filter(
        Evidence.product_id == product_id,
        Evidence.tenant_id == tenant_id
    ).all()
    evidence_list = []
    for ev in evidences:
        evidence_list.append({
            "id": ev.id,
            "source_id": ev.source_id,
            "document_name": ev.document_name,
            "url": ev.url,
            "page": ev.page,
            "section": ev.section,
            "content": ev.content,
            "score": ev.score,
            "source_type": ev.source_type,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        })

    # Source documents
    source_docs = db.query(SourceDocument).filter(
        SourceDocument.product_id == product_id,
        SourceDocument.tenant_id == tenant_id
    ).all()
    sources = []
    for sd in source_docs:
        sources.append({
            "id": sd.id,
            "name": sd.name,
            "type": sd.type,
            "file_size": sd.file_size,
            "url": sd.url,
            "pages": sd.pages,
            "ocr_accuracy": sd.ocr_accuracy,
            "extracted_at": sd.extracted_at.isoformat() if sd.extracted_at else None,
        })

    # Intelligence reasoning from stored JSON
    intelligence = product.intelligence_json or {}
    field_provenance = []

    # Extract field-level provenance from stored intelligence
    attrs = intelligence.get("attributes", [])
    for attr in attrs:
        field_name = attr.get("field_name", "")
        status = attr.get("status", "UNKNOWN")
        value = attr.get("value")
        evidence_snippets = attr.get("evidence", [])
        conflicts = attr.get("conflicts", [])

        field_provenance.append({
            "field_name": field_name,
            "value": value,
            "status": status,
            "confidence": attr.get("confidence", 0.0),
            "reason": attr.get("reason"),
            "evidence_count": len(evidence_snippets),
            "has_conflict": len(conflicts) > 0,
            "supporting_sources": [
                {
                    "source": e.get("source"),
                    "snippet": (e.get("snippet") or e.get("content", ""))[:300],
                    "score": e.get("score"),
                }
                for e in evidence_snippets[:3]
            ],
        })

    return {
        "product_id": product_id,
        "product_name": product.name,
        "sources": sources,
        "evidence": evidence_list,
        "field_provenance": field_provenance,
        "overall_confidence": product.confidence_score,
        "confidence_level": product.confidence_level,
        "missing_fields_count": product.missing_fields_count or 0,
        "conflict_fields_count": product.conflict_fields_count or 0,
    }


@router.get("/explainability/{product_id}/sources", response_model=List[Dict[str, Any]])
def get_product_sources(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Get source documents for a product."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    source_docs = db.query(SourceDocument).filter(
        SourceDocument.product_id == product_id,
        SourceDocument.tenant_id == tenant_id
    ).all()
    return [
        {
            "id": sd.id,
            "name": sd.name,
            "type": sd.type,
            "file_size": sd.file_size,
            "url": sd.url,
            "pages": sd.pages,
            "ocr_accuracy": sd.ocr_accuracy,
            "extracted_at": sd.extracted_at.isoformat() if sd.extracted_at else None,
            "provenance_metadata": sd.provenance_metadata,
        }
        for sd in source_docs
    ]

