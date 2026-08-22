from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from backend.core.db import get_db
from backend.knowledge.official_knowledge import official_knowledge_service
from backend.knowledge.external_acquisition import external_knowledge_provider
from backend.core.storage_safety import storage_safety
from backend.knowledge.dataset_registry import dataset_registry
from backend.schemas.retrieval import EvidenceSchema

router = APIRouter()

@router.get("/knowledge/official/manufacturer-brand")
def lookup_manufacturer_brand(query: str, db: Session = Depends(get_db)):
    result = official_knowledge_service.lookup_manufacturer_brand(db, query)
    if not result:
        raise HTTPException(status_code=404, detail=f"Manufacturer/Brand '{query}' not found in official UniCat master list.")
    return result

@router.get("/knowledge/official/uom/normalize")
def normalize_uom(unit: str, db: Session = Depends(get_db)):
    result = official_knowledge_service.normalize_uom(db, unit)
    if not result:
        raise HTTPException(status_code=404, detail=f"UOM unit '{unit}' not found in official master list.")
    return result

@router.get("/knowledge/storage-stats")
def get_storage_stats(db: Session = Depends(get_db)):
    stats = storage_safety.get_storage_stats()
    
    # Add dataset counts to match schema exactly
    all_datasets = dataset_registry.list_all(db)
    stats["dataset_count"] = len(all_datasets)
    stats["permanent_dataset_count"] = len([d for d in all_datasets if d.permanent])
    stats["temporary_dataset_count"] = len([d for d in all_datasets if not d.permanent])
    return stats

@router.get("/knowledge/baseline/status")
def get_baseline_status(db: Session = Depends(get_db)):
    from backend.knowledge.baseline_knowledge import get_baseline_status as get_status
    return get_status(db)

@router.get("/knowledge/datasets")
def list_datasets(db: Session = Depends(get_db)):
    records = dataset_registry.list_all(db)
    return [
        {
            "id": r.dataset_id,
            "name": r.name,
            "source": r.source,
            "size_bytes": r.size_bytes,
            "permanent": r.permanent,
            "status": r.status
        }
        for r in records
    ]

@router.get("/knowledge/datasets/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    record = dataset_registry.get_by_id(db, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    return record

@router.post("/knowledge/targeted-acquire", response_model=List[EvidenceSchema])
def trigger_targeted_acquisition(
    query: str,
    industry: Optional[str] = None,
    category: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    source_requirements = {
        "industry": industry,
        "category": category
    }
    evidence = external_knowledge_provider.search_and_acquire(
        db=db,
        query=query,
        missing_fields=missing_fields or ["technical_specs"],
        source_requirements=source_requirements
    )
    return evidence
