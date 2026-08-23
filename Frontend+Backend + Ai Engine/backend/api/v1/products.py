import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.db import get_db
from backend.core.auth import get_current_tenant
from backend.schemas.product import ProductCreate, ProductUpdate
from backend.schemas.review import HumanReviewRequest, HumanReviewResponse
from backend.services.product_service import product_service
from backend.services.review_service import review_service
from backend.services.job_service import job_service
from backend.db.models import Product, SourceDocument, Evidence, ValidationResult
from backend.ingestion.catalog_parser import CatalogParser
from backend.knowledge.storage import storage_manager
from backend.core.logging import logger

from backend.schemas.ai_contract import AIProcessingMode
from backend.db.models import ProcessingJob

router = APIRouter()


class UrlIngestRequest(BaseModel):
    url: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None
    ai_mode: AIProcessingMode = AIProcessingMode.AUTO


@router.post("/products/batch-upload", response_model=Dict[str, Any], status_code=202)
async def upload_batch_catalog(
    file: UploadFile = File(...),
    auto_process: bool = Form(True),
    ai_mode: AIProcessingMode = Form(AIProcessingMode.AUTO),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Dedicated catalog spreadsheet ingestion endpoint.
    Parses XLSX/CSV, creates individual Product entities, creates ProcessingJobs,
    and runs the AI ProductIntelligencePipeline in the background for the current tenant.
    """
    filename = file.filename or "catalog_batch.xlsx"
    content_bytes = await file.read()
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"

    # Store raw copy in storage
    storage_manager.store_user_upload(content_bytes, f"{batch_id}_{filename}")

    # Parse spreadsheet into structured rows
    try:
        parse_result = CatalogParser.parse_file(content_bytes, filename)
    except Exception as e:
        logger.error(f"Catalog parsing failed for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse catalog spreadsheet: {str(e)}")

    if parse_result.imported_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"No valid product records found in {filename}. Errors: {'; '.join(parse_result.errors[:5])}"
        )

    # Persist Product records and create ProcessingJobs scoped to tenant_id
    created_product_ids = []
    created_job_ids = []

    for parsed_item in parse_result.parsed_rows:
        try:
            prod = product_service.create_product(
                db=db,
                payload=parsed_item.product_data,
                extra_attributes=parsed_item.raw_attributes,
                tenant_id=tenant_id
            )
            created_product_ids.append(prod.id)

            if auto_process:
                job = job_service.create_job(db, prod.id, tenant_id=tenant_id, ai_mode=ai_mode)
                created_job_ids.append(job.id)
        except Exception as e:
            logger.error(f"Error creating product row {parsed_item.row_number}: {e}")
            parse_result.errors.append(f"Row {parsed_item.row_number} DB save error: {str(e)}")

    logger.info(
        f"Batch {batch_id} imported {len(created_product_ids)} products "
        f"from {filename} (Tenant: {tenant_id})"
    )

    # Launch multi-agent pipeline in background
    if auto_process and created_job_ids and background_tasks:
        background_tasks.add_task(job_service.run_batch_jobs, created_job_ids)

    return {
        "batch_id": batch_id,
        "filename": filename,
        "total_rows": parse_result.total_rows,
        "imported_count": len(created_product_ids),
        "skipped_count": parse_result.skipped_count,
        "headers_detected": parse_result.headers_detected,
        "errors": parse_result.errors[:10],
        "job_ids": created_job_ids,
        "product_ids": created_product_ids,
        "message": f"Successfully ingested {len(created_product_ids)} products from {filename}. Background intelligence processing initiated.",
    }


@router.post("/products", response_model=Dict[str, Any], status_code=201)
async def create_product(
    payload: ProductCreate,
    auto_process: bool = Query(True, description="Automatically trigger AI intelligence pipeline"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.create_product(db, payload, tenant_id=tenant_id)

    if auto_process:
        job = job_service.create_job(db, product.id, tenant_id=tenant_id, ai_mode=payload.ai_mode)
        await job_service.run_pipeline(db, job.id)
        db.refresh(product)

    return product_service.format_to_response(product)


@router.post("/products/from-url", response_model=Dict[str, Any], status_code=201)
async def create_product_from_url(
    payload: UrlIngestRequest,
    auto_process: bool = Query(True),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Ingest a product from URL and run multi-agent intelligence extraction.
    """
    name = payload.product_name or f"Product from {payload.url.split('//')[-1].split('/')[0]}"
    sku = payload.sku or payload.url.split('/')[-1].split('?')[0].replace('-', '_')[:30]

    create_dto = ProductCreate(
        name=name,
        sku=sku,
        mpn=sku,
        category=payload.category or "Industrial Equipment",
        description=f"Ingested from {payload.url}. {payload.note or ''}",
        url=payload.url,
        ai_mode=payload.ai_mode
    )
    product = product_service.create_product(db, create_dto, tenant_id=tenant_id)

    # Store source document for URL
    source_doc = SourceDocument(
        tenant_id=tenant_id,
        product_id=product.id,
        name=payload.url,
        type="url",
        url=payload.url,
        pages=1,
        ocr_accuracy=100.0,
        provenance_metadata={"origin": "url_ingestion", "url": payload.url}
    )
    db.add(source_doc)
    db.commit()

    if auto_process:
        job = job_service.create_job(db, product.id, tenant_id=tenant_id, ai_mode=payload.ai_mode)
        await job_service.run_pipeline(db, job.id)
        db.refresh(product)

    return product_service.format_to_response(product)


@router.get("/products", response_model=List[Dict[str, Any]])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    confidence_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    products = product_service.list_products(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        status=status,
        confidence_level=confidence_level,
        tenant_id=tenant_id
    )
    return [product_service.format_to_response(p) for p in products]


@router.get("/products/{product_id}", response_model=Dict[str, Any])
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    return product_service.format_to_response(product)


@router.put("/products/{product_id}", response_model=Dict[str, Any])
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.update_product(db, product_id, payload, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    return product_service.format_to_response(product)


@router.delete("/products/{product_id}", response_model=Dict[str, Any])
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    success = product_service.delete_product(db, product_id, tenant_id=tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    return {"message": f"Product {product_id} deleted successfully.", "id": product_id}


@router.post("/products/{product_id}/process", response_model=Dict[str, Any], status_code=202)
async def process_product(
    product_id: str,
    background: bool = Query(False, description="Run in background task if True"),
    ai_mode: Optional[AIProcessingMode] = Query(None, description="Override AI mode"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    prev_job = db.query(ProcessingJob).filter(ProcessingJob.product_id == product_id).order_by(ProcessingJob.created_at.desc()).first()
    resolved_ai_mode = ai_mode or (AIProcessingMode(prev_job.ai_mode) if prev_job else AIProcessingMode.AUTO)

    job = job_service.create_job(db, product_id, tenant_id=tenant_id, ai_mode=resolved_ai_mode)

    if background and background_tasks:
        background_tasks.add_task(_run_job_bg, job.id)
        return {
            "message": f"Processing job {job.id} enqueued in background.",
            "job_id": job.id,
            "status": "QUEUED",
            "product_id": product_id,
            "ai_mode": job.ai_mode
        }
    else:
        # Run synchronously for immediate complete result
        completed_job = await job_service.run_pipeline(db, job.id)
        db.refresh(product)
        return {
            "message": f"Processing job {completed_job.id} completed.",
            "job_id": completed_job.id,
            "status": completed_job.status,
            "pipeline_stage": completed_job.pipeline_stage,
            "product": product_service.format_to_response(product),
            "ai_mode": completed_job.ai_mode
        }


@router.post("/products/{product_id}/reprocess", response_model=Dict[str, Any], status_code=202)
async def reprocess_product(
    product_id: str,
    ai_mode: Optional[AIProcessingMode] = Query(None, description="Override AI mode"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    prev_job = db.query(ProcessingJob).filter(ProcessingJob.product_id == product_id).order_by(ProcessingJob.created_at.desc()).first()
    resolved_ai_mode = ai_mode or (AIProcessingMode(prev_job.ai_mode) if prev_job else AIProcessingMode.AUTO)

    job = job_service.create_job(db, product_id, tenant_id=tenant_id, ai_mode=resolved_ai_mode)
    completed_job = await job_service.run_pipeline(db, job.id)
    db.refresh(product)
    return {
        "message": f"Reprocessing job {completed_job.id} completed.",
        "job_id": completed_job.id,
        "status": completed_job.status,
        "product": product_service.format_to_response(product),
        "ai_mode": completed_job.ai_mode
    }


@router.get("/products/{product_id}/intelligence", response_model=Dict[str, Any])
def get_product_intelligence(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """Direct endpoint to fetch the full structured intelligence document."""
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    formatted = product_service.format_to_response(product)
    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "brand": product.brand,
        "manufacturer": product.manufacturer,
        "category": product.category,
        "industry": product.industry,
        "description": product.description,
        "status": product.status,
        "confidenceLevel": product.confidence_level,
        "completenessScore": product.completeness_score,
        "missingFieldsCount": product.missing_fields_count,
        "conflictFieldsCount": product.conflict_fields_count,
        "dynamicAttributes": formatted.get("dynamicAttributes", []),
        "technicalSpecs": formatted.get("technicalSpecs", []),
        "dimensions": formatted.get("dimensions", []),
        "materials": formatted.get("materials", []),
        "certifications": formatted.get("certifications", []),
        "features": formatted.get("features", []),
        "applications": formatted.get("applications", []),
        "validationIssues": formatted.get("validationIssues", []),
        "intelligence": product.intelligence_json or {},
        "commerceData": product.commerce_json or {}
    }


@router.get("/products/{product_id}/sources", response_model=List[Dict[str, Any]])
def get_product_sources(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    docs = db.query(SourceDocument).filter(
        SourceDocument.product_id == product_id,
        SourceDocument.tenant_id == tenant_id
    ).all()
    return [
        {
            "id": sd.id,
            "name": sd.name,
            "type": sd.type,
            "fileSize": sd.file_size,
            "url": sd.url,
            "pages": sd.pages,
            "extractedAt": sd.extracted_at.isoformat() if sd.extracted_at else None
        }
        for sd in docs
    ]


@router.get("/products/{product_id}/validation", response_model=List[Dict[str, Any]])
def get_product_validation(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    issues = db.query(ValidationResult).filter(
        ValidationResult.product_id == product_id,
        ValidationResult.tenant_id == tenant_id
    ).all()
    return [
        {
            "id": issue.id,
            "severity": issue.severity,
            "type": issue.type,
            "field": issue.field,
            "message": issue.message,
            "currentValue": issue.current_value,
            "suggestedValue": issue.suggested_value,
            "sourceA": issue.source_a,
            "sourceB": issue.source_b,
            "resolved": issue.resolved
        }
        for issue in issues
    ]


@router.post("/products/{product_id}/review", response_model=HumanReviewResponse)
def review_product(
    product_id: str,
    payload: HumanReviewRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    try:
        review_res = review_service.submit_review(db, product_id, payload)
        return review_res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _run_job_bg(job_id: str):
    import asyncio
    from backend.core.db import SessionLocal
    db = SessionLocal()
    try:
        asyncio.run(job_service.run_pipeline(db, job_id))
    finally:
        db.close()


@router.get("/products/{product_id}/export/xlsx")
def export_product_xlsx(
    product_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    import io
    import sys
    import os
    from fastapi.responses import Response

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

    try:
        import pandas as pd
        from ai_engine.output.commerce_adapter import CommerceOutputAdapter, COMMERCE_COLUMNS
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Failed to import export dependencies: {e}")

    product = product_service.get_product(db, product_id, tenant_id=tenant_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")

    if not product.commerce_json:
        raise HTTPException(status_code=400, detail="Product has no commerce output generated.")

    try:
        df = pd.DataFrame([product.commerce_json])

        if len(df.columns) != 252:
            raise HTTPException(status_code=500, detail=f"Internal schema error: export has {len(df.columns)} columns instead of 252.")

        for expected, actual in zip(COMMERCE_COLUMNS, df.columns):
            if expected != actual:
                raise HTTPException(status_code=500, detail=f"Internal schema error: column mismatch '{expected}' != '{actual}'")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Delivery Format')

        output.seek(0)

        filename = f"Unihack_{product.sku or product_id}.xlsx".replace(" ", "_")
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }

        return Response(content=output.read(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
