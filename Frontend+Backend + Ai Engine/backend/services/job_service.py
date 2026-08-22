"""
Job Service — state machine and processing coordinator.

Pipeline stages:
    QUEUED → LOCAL_RETRIEVAL → EVIDENCE_SUFFICIENCY_CHECK
    → EXTERNAL_ACQUISITION (if needed) → AI_ENGINE_PROCESSING
    → DETERMINISTIC_VALIDATION → COMPLETED | FAILED

The actual intelligence generation delegates to the Hackathon AI pipeline
via pipeline_adapter.run_intelligence_pipeline().
"""
from __future__ import annotations
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import Optional, List

from backend.db.models import ProcessingJob, Product, Attribute, Evidence, ValidationResult
from backend.schemas.job import JobStatusResponse
from backend.retrieval.retrieval_service import retrieval_service
from backend.knowledge.external_acquisition import external_knowledge_provider
from backend.services.product_service import product_service
from backend.integration.output_adapter import (
    extract_persistence_data,
    extract_attributes_from_result,
    extract_evidence_from_result,
    extract_validation_issues_from_result,
)
from backend.schemas.ai_contract import AIServiceRequest, AIProcessingMode
from backend.integration.engine_service import integrated_ai_service
from backend.core.logging import logger

class JobService:
    """
    Manages job lifecycle and delegates intelligence processing to Hackathon AI pipeline.

    State machine:
        QUEUED → PROCESSING/LOCAL_RETRIEVAL → PROCESSING/EVIDENCE_SUFFICIENCY_CHECK
        → PROCESSING/EXTERNAL_ACQUISITION (conditional) → PROCESSING/AI_ENGINE_PROCESSING
        → PROCESSING/DETERMINISTIC_VALIDATION → COMPLETED | FAILED
    """

    def create_job(self, db: Session, product_id: str, tenant_id: Optional[str] = None, ai_mode: AIProcessingMode = AIProcessingMode.AUTO) -> ProcessingJob:
        if not tenant_id:
            prod = db.query(Product).filter(Product.id == product_id).first()
            tenant_id = prod.tenant_id if prod else "demo"

        job = ProcessingJob(
            tenant_id=tenant_id,
            product_id=product_id,
            status="QUEUED",
            step="INIT",
            pipeline_stage="QUEUED",
            progress=0,
            ai_mode=ai_mode.value,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(f"Created processing job {job.id} for product {product_id} with AI Mode {ai_mode} (Tenant: {tenant_id})")
        return job

    def get_job(self, db: Session, job_id: str, tenant_id: Optional[str] = None) -> Optional[ProcessingJob]:
        query = db.query(ProcessingJob).filter(ProcessingJob.id == job_id)
        if tenant_id:
            query = query.filter(ProcessingJob.tenant_id == tenant_id)
        return query.first()

    def list_jobs(self, db: Session, skip: int = 0, limit: int = 50, status: Optional[str] = None, tenant_id: Optional[str] = None) -> List[ProcessingJob]:
        query = db.query(ProcessingJob)
        if tenant_id:
            query = query.filter(ProcessingJob.tenant_id == tenant_id)
        if status:
            query = query.filter(ProcessingJob.status == status.upper())
        return query.order_by(ProcessingJob.created_at.desc()).offset(skip).limit(limit).all()

    async def run_pipeline(self, db: Session, job_id: str) -> ProcessingJob:
        """
        Execute the full product intelligence pipeline for a job.

        Steps:
        1. Retrieve local knowledge evidence
        2. Check evidence sufficiency
        3. If insufficient, perform external acquisition
        4. Run Hackathon multi-agent AI pipeline
        5. Persist structured intelligence results with tenant isolation & deduplication
        6. Mark job complete
        """
        job = self.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        try:
            # ── Step 1: Mark processing start ──────────────────────────────────
            job.status = "PROCESSING"
            job.step = "LOCAL_RETRIEVAL"
            job.pipeline_stage = "RETRIEVING"
            job.progress = 10
            db.commit()

            product = db.query(Product).filter(Product.id == job.product_id).first()
            if not product:
                raise ValueError(f"Product {job.product_id} not found.")

            tenant_id = product.tenant_id or job.tenant_id or "demo"
            job.tenant_id = tenant_id

            # ── Step 2: Local Knowledge Retrieval ─────────────────────────────
            query_str = f"{product.brand or ''} {product.name} {product.mpn or product.sku or ''}".strip()
            retrieved_evidence = await run_in_threadpool(retrieval_service.search, query_str, 5)

            job.progress = 25
            db.commit()

            # ── Step 3: Evidence Sufficiency Check ───────────────────────────
            job.step = "EVIDENCE_SUFFICIENCY_CHECK"
            job.pipeline_stage = "DISCOVERING"
            job.progress = 30
            db.commit()

            if len(retrieved_evidence) < 1:
                # ── Step 4: External Acquisition (if local insufficient) ──────
                job.step = "EXTERNAL_ACQUISITION"
                job.progress = 40
                db.commit()
                logger.info(f"Local evidence insufficient for job {job.id}. Triggering external acquisition.")

                missing_fields = []
                if not product.category:
                    missing_fields.append("category")
                if not product.brand:
                    missing_fields.append("brand")
                missing_fields.append("technical_specs")

                ext_evidence = await run_in_threadpool(
                    external_knowledge_provider.search_and_acquire,
                    db=db,
                    query=query_str,
                    missing_fields=missing_fields,
                    source_requirements={
                        "industry": product.industry or "",
                        "category": product.category or "",
                    }
                )
                retrieved_evidence.extend(ext_evidence)

            # ── Step 5: Hackathon AI Engine Processing ────────────────────────
            job.step = "AI_ENGINE_PROCESSING"
            job.pipeline_stage = "ENRICHING"
            job.progress = 50
            db.commit()

            product_data = {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "mpn": product.mpn,
                "brand": product.brand,
                "manufacturer": product.manufacturer,
                "category": product.category,
                "subcategory": product.subcategory,
                "industry": product.industry,
                "description": product.description,
            }

            # Map the job's ai_mode string back to the Enum
            try:
                ai_mode_enum = AIProcessingMode(job.ai_mode)
            except ValueError:
                logger.warning(f"Invalid ai_mode '{job.ai_mode}' on job {job.id}, defaulting to AUTO")
                ai_mode_enum = AIProcessingMode.AUTO

            # Call the authoritative Hackathon multi-agent pipeline
            ai_request = AIServiceRequest(
                product_input=product_data,
                ai_mode=ai_mode_enum,
                metadata={
                    "trace_id": job.id,
                    "job_id": job.id,
                    "product_id": job.product_id,
                    "tenant_id": tenant_id
                }
            )
            
            from backend.integration.engine_service import _backend_request_to_product_input
            ai_engine_input = _backend_request_to_product_input(ai_request)
            
            # Add trace_context to ai_engine_input metadata
            if not ai_engine_input.metadata:
                ai_engine_input.metadata = {}
            ai_engine_input.metadata["trace_id"] = job.id
            ai_engine_input.metadata["job_id"] = job.id
            ai_engine_input.metadata["product_id"] = job.product_id
            ai_engine_input.metadata["tenant_id"] = tenant_id

            
            pipeline_result = await integrated_ai_service.process_intelligence(
                product_input=ai_engine_input,
                pre_retrieved_evidence=retrieved_evidence,
                ai_mode=ai_mode_enum,
            )

            job.pipeline_stage = "VALIDATING"
            job.progress = 80
            db.commit()

            # ── Step 6: Persist Intelligence Results ──────────────────────────
            persistence_data = extract_persistence_data(pipeline_result)
            new_attributes = extract_attributes_from_result(pipeline_result)
            new_evidence = extract_evidence_from_result(pipeline_result)
            validation_issues = extract_validation_issues_from_result(pipeline_result)

            # Update product with AI-generated intelligence
            for key, value in persistence_data.items():
                if hasattr(product, key):
                    setattr(product, key, value)

            # Update descriptions from intelligence result
            if pipeline_result.success and pipeline_result.intelligence:
                intel = pipeline_result.intelligence
                if intel.identity:
                    if intel.identity.category:
                        product.category = product.category or intel.identity.category
                    if intel.identity.industry:
                        product.industry = product.industry or intel.identity.industry
                    if intel.identity.brand:
                        product.brand = product.brand or intel.identity.brand
                    if intel.identity.manufacturer:
                        product.manufacturer = product.manufacturer or intel.identity.manufacturer

                if intel.short_description and intel.short_description.value:
                    product.description = intel.short_description.value

            # Clear and replace attributes for this product (idempotent)
            db.query(Attribute).filter(Attribute.product_id == product.id).delete()
            for attr_data in new_attributes:
                db_attr = Attribute(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    attribute_type=attr_data.get("attribute_type", "technical_spec"),
                    key=attr_data.get("key", ""),
                    value=attr_data.get("value"),
                    normalized_value=attr_data.get("normalized_value"),
                    unit=attr_data.get("unit"),
                    confidence=attr_data.get("confidence", 0.0),
                    status=attr_data.get("status", "ai_inferred"),
                    field_status=attr_data.get("field_status"),
                    source_snippet=attr_data.get("source_snippet"),
                    source_location=attr_data.get("source_location"),
                    explanation=attr_data.get("explanation"),
                    competing_value=attr_data.get("competing_value"),
                )
                db.add(db_attr)

            # Clear and replace evidence for this product (idempotent)
            db.query(Evidence).filter(Evidence.product_id == product.id).delete()
            for ev_data in new_evidence:
                db_ev = Evidence(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    source_id=ev_data.get("source_id"),
                    document_name=ev_data.get("document_name"),
                    url=ev_data.get("url"),
                    page=ev_data.get("page"),
                    section=ev_data.get("section"),
                    content=ev_data.get("content", ""),
                    score=ev_data.get("score", 0.0),
                    source_type=ev_data.get("source_type"),
                    provenance_json=ev_data.get("provenance_json"),
                )
                db.add(db_ev)

            # Clear and replace validation results for this product (idempotent deduplication)
            db.query(ValidationResult).filter(ValidationResult.product_id == product.id).delete()
            for issue in validation_issues:
                db_issue = ValidationResult(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    severity=issue.get("severity", "medium"),
                    type=issue.get("type", "validation_failure"),
                    field=issue.get("field", "unknown"),
                    message=issue.get("message", ""),
                    current_value=issue.get("current_value"),
                    suggested_value=issue.get("suggested_value"),
                    source_a=issue.get("source_a"),
                    source_b=issue.get("source_b"),
                )
                db.add(db_issue)

            db.commit()

            # ── Step 7: Complete Job ───────────────────────────────────────────
            if pipeline_result.success:
                job.status = "COMPLETED"
                job.step = "FINISHED"
                job.pipeline_stage = "COMPLETED"
            else:
                job.status = "FAILED"
                job.step = "ERROR"
                job.pipeline_stage = "FAILED"
                job.error_message = ", ".join([e.message for e in pipeline_result.errors]) if getattr(pipeline_result, "errors", None) else "AI Pipeline failed."
            job.progress = 100
            job.processing_time_ms = pipeline_result.processing_time_ms
            job.result_json = {
                "product_id": product.id,
                "validation_status": persistence_data.get("status"),
                "confidence_level": persistence_data.get("confidence_level"),
                "completeness_score": persistence_data.get("completeness_score"),
                "fields_total": persistence_data.get("fields_total"),
                "fields_populated": persistence_data.get("fields_populated"),
                "missing_fields_count": persistence_data.get("missing_fields_count"),
                "conflict_fields_count": persistence_data.get("conflict_fields_count"),
                "evidence_count": len(retrieved_evidence),
                "processing_time_ms": pipeline_result.processing_time_ms,
            }
            db.commit()
            db.refresh(job)
            logger.info(
                f"Pipeline completed for job {job.id} (Tenant: {tenant_id}) — "
                f"status={persistence_data.get('status')}, "
                f"confidence={persistence_data.get('confidence_level')}"
            )
            return job

        except Exception as e:
            error_msg = str(e)
            # Unwrap tenacity.RetryError
            if type(e).__name__ == "RetryError" and hasattr(e, "last_attempt"):
                try:
                    inner = e.last_attempt.exception()
                    if inner:
                        error_msg = str(inner)
                except Exception:
                    pass

            logger.error(f"Pipeline failure for job {job.id}: {error_msg}", exc_info=True)
            job.status = "FAILED"
            job.step = "ERROR"
            job.pipeline_stage = "FAILED"
            job.error_message = error_msg
            db.commit()
            db.refresh(job)
            return job

    def run_batch_jobs(self, job_ids: List[str]):
        """
        Execute a list of processing jobs in sequence in a background worker context.
        Opens and manages a dedicated DB session per job.
        """
        from backend.core.db import SessionLocal
        import time
        import asyncio
        logger.info(f"Starting background batch execution of {len(job_ids)} jobs")

        for i, job_id in enumerate(job_ids):
            db = SessionLocal()
            try:
                logger.info(f"Batch processing item {i+1}/{len(job_ids)} (Job: {job_id})")
                # This retry block runs in a thread in background tasks, so asyncio.run is safe
                asyncio.run(self.run_pipeline(db, job_id))
            except Exception as e:
                logger.error(f"Batch execution failed for job {job_id}: {e}")
            finally:
                db.close()
                
            # Throttle to respect Gemini rate limits (max 15 requests per minute for free tier)
            if i < len(job_ids) - 1:
                logger.info("Throttling for 20 seconds before next batch item to respect API limits...")
                time.sleep(20)

        logger.info(f"Completed background batch execution of {len(job_ids)} jobs")


job_service = JobService()


