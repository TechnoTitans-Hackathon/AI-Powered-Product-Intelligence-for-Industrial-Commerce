import os
import json
import hashlib
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.knowledge.dataset_registry import dataset_registry
from backend.knowledge.storage import storage_manager
from backend.retrieval.retrieval_service import retrieval_service
from backend.schemas.source import ProcessedSource
from backend.core.config import settings
from backend.core.logging import logger

# Path to the baseline data files (shipped with the codebase)
BASELINE_DIR = os.path.join(os.path.dirname(__file__), "baseline")


def _file_checksum(filepath: str) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_and_register_baseline_file(
    db: Session,
    filename: str,
    dataset_id: str,
    name: str,
    description: str,
    purpose: str,
    industries: list,
) -> bool:
    """
    Load a baseline JSON file, store it in permanent knowledge,
    register it in the dataset registry, and index its content.
    Returns True if newly registered, False if already existed.
    """
    filepath = os.path.join(BASELINE_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"Baseline file not found: {filepath}")
        return False

    file_size = os.path.getsize(filepath)
    checksum = _file_checksum(filepath)

    # Check duplicate
    existing = dataset_registry.get_by_id(db, dataset_id)
    if existing:
        logger.info(f"Baseline dataset '{dataset_id}' already registered. Skipping.")
        return False

    from backend.core.storage_safety import storage_safety
    if not storage_safety.check_permanent_storage(file_size):
        logger.error(f"Cannot load baseline dataset '{dataset_id}'. Permanent limit exceeded.")
        return False

    # Read content
    with open(filepath, "rb") as f:
        content_bytes = f.read()

    # Store in permanent knowledge directory
    perm_filename = f"baseline_{dataset_id}.json"
    storage_manager.store_permanent_knowledge(content_bytes, perm_filename)

    # Register in dataset registry
    dataset_registry.register(
        db=db,
        dataset_id=dataset_id,
        name=name,
        source="Curated Reference",
        source_url="",
        license="curated-reference",
        size_bytes=file_size,
        checksum=checksum,
        version="1.0",
        industries=industries,
        categories=[],
        description=description,
        purpose=purpose,
        permanent=True,
        status="active"
    )

    # Index content for retrieval
    try:
        content_text = content_bytes.decode("utf-8")
        processed = ProcessedSource(
            source_id=f"baseline_{dataset_id}",
            original_file=perm_filename,
            source_type="json",
            extracted_text=content_text[:10000],  # Index first 10K chars
            metadata={
                "dataset_id": dataset_id,
                "purpose": purpose,
                "permanent": True,
            },
        )
        retrieval_service.index_processed_source(processed)
    except Exception as e:
        logger.warning(f"Could not index baseline dataset '{dataset_id}': {e}")

    logger.info(f"Baseline dataset '{dataset_id}' loaded and registered ({file_size} bytes).")
    return True


def initialize_baseline_knowledge(db: Session) -> Dict[str, Any]:
    """
    Initialize the permanent baseline knowledge corpus on startup.
    Called once during application initialization.
    """
    logger.info("Initializing permanent baseline knowledge corpus...")
    
    # 1. Industry Taxonomy
    _load_and_register_baseline_file(
        db=db,
        filename="industry_taxonomy.json",
        dataset_id="baseline_industry_taxonomy",
        name="Industry & Product Taxonomy",
        description="Hierarchical taxonomy: industry -> category -> subcategory for 15+ industrial/commercial domains.",
        purpose="baseline_taxonomy",
        industries=[
            "Industrial Equipment", "Industrial Automation", "Electrical Components",
            "Fasteners", "HVAC", "Safety Equipment", "Automotive Components",
            "Construction Materials", "Power Equipment", "Agricultural Equipment",
            "Packaging Equipment", "Manufacturing Equipment", "Chemicals and Materials",
            "Medical and Regulated Products"
        ],
    )

    # 2. Attribute Patterns
    _load_and_register_baseline_file(
        db=db,
        filename="attribute_patterns.json",
        dataset_id="baseline_attribute_patterns",
        name="Product Attribute Patterns",
        description="Common technical attribute keys, units, and data types per product category.",
        purpose="baseline_attributes",
        industries=[
            "Industrial Equipment", "Industrial Automation", "Fasteners"
        ],
    )

    return get_baseline_status(db)

def get_baseline_status(db: Session) -> Dict[str, Any]:
    from backend.core.storage_safety import storage_safety
    
    datasets = dataset_registry.list_permanent(db)
    actual_bytes = storage_safety.get_directory_size(settings.PERMANENT_KNOWLEDGE_PATH)
    
    industries = set()
    categories = set()
    for d in datasets:
        for ind in d.industries:
            industries.add(ind)
        for cat in d.categories:
            categories.add(cat)
            
    # The requirement strictly asks to not say initialized = true if corpus is basically empty.
    # We will assume a minimal threshold (e.g. at least some actual product knowledge datasets)
    # The user states: "Target: 1.5 - 2.0 GiB. If it's only 700 MiB, keep 700 MiB."
    # We will mark it as initialized=True if actual_bytes > 0, but the status will clearly report size.
    # Wait, "If no real baseline exists: initialized = false"
    # A few KB of taxonomy is not a real baseline.
    initialized = actual_bytes > (1024 * 1024) # 1 MB threshold for real baseline
    
    return {
        "initialized": initialized,
        "actual_bytes": actual_bytes,
        "target_bytes": int(storage_safety.max_permanent_bytes * 0.75),
        "dataset_count": len(datasets),
        "industry_count": len(industries),
        "category_count": len(categories)
    }
