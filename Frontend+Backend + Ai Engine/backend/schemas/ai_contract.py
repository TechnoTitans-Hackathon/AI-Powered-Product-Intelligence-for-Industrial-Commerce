from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.schemas.retrieval import EvidenceSchema

class AIProcessingMode(str, Enum):
    AUTO = "AUTO"
    FAST = "FAST"
    DEEP = "DEEP"
    LOCAL = "LOCAL"

class DiscoveryContextContract(BaseModel):
    product_category: Optional[str] = ""
    industry: Optional[str] = ""
    attributes_required: List[str] = []
    missing_information: List[str] = []
    retrieval_queries: List[str] = []
    evidence_sufficiency: Dict[str, Any] = Field(default_factory=dict)

class AIServiceRequest(BaseModel):
    product_input: Dict[str, Any]
    ai_mode: AIProcessingMode = AIProcessingMode.AUTO
    discovery: DiscoveryContextContract = Field(default_factory=DiscoveryContextContract)
    retrieved_evidence: List[EvidenceSchema] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AIAttributeItem(BaseModel):
    key: str
    value: str
    normalized_value: Optional[str] = None
    unit: Optional[str] = None
    attribute_type: str = "technical_spec" # technical_spec, dimension, material, certification, compatibility
    confidence: float = Field(default=80.0, ge=0.0, le=100.0)
    source_snippet: Optional[str] = None
    source_location: Optional[str] = None
    explanation: Optional[str] = None
    competing_value: Optional[str] = None

class AIServiceResponse(BaseModel):
    product: Dict[str, Any]
    attributes: List[AIAttributeItem] = []
    descriptions: Dict[str, Any] = Field(default_factory=dict)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    sources: List[Dict[str, Any]] = []
    evidence: List[EvidenceSchema] = []
    explanation: Dict[str, Any] = Field(default_factory=dict)
    validation_hints: List[str] = []
    review_required: bool = False
