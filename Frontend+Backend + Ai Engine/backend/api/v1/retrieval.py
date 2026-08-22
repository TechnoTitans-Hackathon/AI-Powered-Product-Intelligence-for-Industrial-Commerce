from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.db import get_db
from backend.schemas.retrieval import RetrievalQuery, RetrievalResponse
from backend.retrieval.retrieval_service import retrieval_service

router = APIRouter()

@router.post("/retrieval/search", response_model=RetrievalResponse)
def search_knowledge(payload: RetrievalQuery, db: Session = Depends(get_db)):
    results = retrieval_service.search(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters
    )
    return RetrievalResponse(
        query=payload.query,
        total_found=len(results),
        evidence=results
    )
