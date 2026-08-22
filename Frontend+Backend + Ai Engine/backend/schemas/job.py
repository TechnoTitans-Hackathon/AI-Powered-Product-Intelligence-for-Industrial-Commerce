from pydantic import BaseModel
from typing import Optional, Dict, Any

class JobStatusResponse(BaseModel):
    job_id: str
    product_id: str
    status: str # QUEUED, PROCESSING, COMPLETED, FAILED, NEEDS_REVIEW
    step: str
    progress: int # 0 - 100
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
