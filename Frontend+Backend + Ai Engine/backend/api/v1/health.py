from fastapi import APIRouter
from backend.core.config import settings
from backend.core.storage_safety import storage_safety
from backend.retrieval.vector_store import vector_store

router = APIRouter()

@router.get("/health")
def health_check():
    storage_stats = storage_safety.get_storage_stats()
    vstore_health = vector_store.health()
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "storage_stats": storage_stats,
        "vector_store": vstore_health
    }
