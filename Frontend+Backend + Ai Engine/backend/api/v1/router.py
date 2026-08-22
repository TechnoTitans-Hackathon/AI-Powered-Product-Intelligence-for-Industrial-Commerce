from fastapi import APIRouter
from backend.api.v1 import (
    health,
    auth,
    products,
    uploads,
    jobs,
    validation,
    analytics,
    explainability,
    retrieval,
    knowledge,
    processing,
    traces,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication & Tenants"])
api_router.include_router(products.router, tags=["Products"])
api_router.include_router(uploads.router, tags=["Uploads"])
api_router.include_router(jobs.router, tags=["Jobs & Batches"])
api_router.include_router(validation.router, tags=["Validation Center"])
api_router.include_router(analytics.router, tags=["Analytics"])
api_router.include_router(explainability.router, tags=["Explainability"])
api_router.include_router(retrieval.router, tags=["Retrieval"])
api_router.include_router(knowledge.router, tags=["Knowledge"])
api_router.include_router(processing.router, tags=["Processing"])
api_router.include_router(traces.router, prefix="/traces", tags=["Traces"])

