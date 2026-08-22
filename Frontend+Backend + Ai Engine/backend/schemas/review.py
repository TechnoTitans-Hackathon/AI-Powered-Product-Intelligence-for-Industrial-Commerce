from pydantic import BaseModel
from typing import Optional

class HumanReviewRequest(BaseModel):
    reviewer: str
    action: str # APPROVED, REJECTED, EDITED
    comment: Optional[str] = None
    field_name: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None

class HumanReviewResponse(BaseModel):
    review_id: str
    product_id: str
    reviewer: str
    action: str
    comment: Optional[str] = None
    field_name: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: str
