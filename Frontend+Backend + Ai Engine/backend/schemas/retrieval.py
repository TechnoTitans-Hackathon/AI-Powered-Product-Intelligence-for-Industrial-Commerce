from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class RetrievalFilter(BaseModel):
    category: Optional[str] = None
    industry: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    source_type: Optional[str] = None
    min_score: Optional[float] = None
    source_id: Optional[str] = None

class RetrievalQuery(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[RetrievalFilter] = None

class EvidenceSchema(BaseModel):
    evidence_id: str
    source_id: str
    document_id: Optional[str] = None
    source: str
    document: str
    url: Optional[str] = None
    page: Optional[int] = None
    timestamp: Optional[str] = None
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}

class RetrievalResponse(BaseModel):
    query: str
    total_found: int
    evidence: List[EvidenceSchema]
