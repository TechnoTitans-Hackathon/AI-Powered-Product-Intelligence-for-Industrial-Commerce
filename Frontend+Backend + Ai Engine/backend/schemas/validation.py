from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ValidationCheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str

class ValidationResponse(BaseModel):
    product_id: str
    status: str # PASS, WARNING, FAILED, NEEDS_REVIEW
    score: float # 0 - 100
    errors: List[str] = []
    warnings: List[str] = []
    checks: List[ValidationCheckResult] = []
    validation_issues: List[Dict[str, Any]] = []
