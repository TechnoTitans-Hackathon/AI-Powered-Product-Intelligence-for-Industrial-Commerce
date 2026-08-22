from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    page: int

class TechnicalSpec(BaseModel):
    id: Optional[str] = None
    key: str
    value: str
    unit: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = "ai_inferred" # verified, ai_inferred, conflicting, missing
    sourceSnippet: Optional[str] = None
    sourceLocation: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    explanation: Optional[str] = None
    competingValue: Optional[str] = None

class DimensionSpec(BaseModel):
    id: Optional[str] = None
    parameter: str
    value: str
    unit: str
    normalizedValue: str
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = "ai_inferred"
    sourceSnippet: Optional[str] = None
    sourceLocation: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    explanation: Optional[str] = None

class VerifiedAttribute(BaseModel):
    id: Optional[str] = None
    value: str
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = "verified"
    sourceSnippet: Optional[str] = None
    sourceLocation: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    explanation: Optional[str] = None

class CompatibilityItem(BaseModel):
    id: Optional[str] = None
    targetSku: str
    targetName: str
    relationship: str # Direct Replacement, Accessory / Part, Mating Assembly, Maintenance Kit
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = "verified"
    explanation: Optional[str] = None

class ValidationIssueSchema(BaseModel):
    id: Optional[str] = None
    severity: str # critical, high, medium, low
    type: str # conflict, missing_field, duplicate, unit_mismatch, non_standard_name
    field: str
    message: str
    sourceA: Optional[str] = None
    sourceB: Optional[str] = None
    resolved: bool = False

class SourceDocumentSchema(BaseModel):
    id: Optional[str] = None
    name: str
    type: str # pdf, excel, url, image, doc, text, video
    fileSize: Optional[str] = None
    url: Optional[str] = None
    pages: Optional[int] = None
    extractedAt: Optional[str] = None
    ocrAccuracy: float = 100.0

class SeoMetadataSchema(BaseModel):
    title: str = ""
    metaDescription: str = ""
    keywords: List[str] = []

from backend.schemas.ai_contract import AIProcessingMode

class ProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    mpn: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    imageUrl: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    ai_mode: AIProcessingMode = Field(default=AIProcessingMode.AUTO)

class UrlIngestRequest(BaseModel):
    url: str
    ai_mode: AIProcessingMode = Field(default=AIProcessingMode.AUTO)

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    mpn: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    status: Optional[str] = None
    review_status: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    sku: str
    name: str
    brand: str
    manufacturer: Optional[str] = None
    category: str
    subcategory: Optional[str] = ""
    industry: Optional[str] = None
    description: str
    completenessScore: float
    confidenceScore: float
    status: str
    review_status: str
    sourceDocument: Optional[SourceDocumentSchema] = None
    imageUrl: str = ""
    technicalSpecs: List[TechnicalSpec] = []
    dimensions: List[DimensionSpec] = []
    materials: List[VerifiedAttribute] = []
    certifications: List[VerifiedAttribute] = []
    compatibility: List[CompatibilityItem] = []
    seo: SeoMetadataSchema = Field(default_factory=SeoMetadataSchema)
    images: List[str] = []
    duplicateCandidateId: Optional[str] = None
    duplicateMatchScore: Optional[float] = None
    validationIssues: List[ValidationIssueSchema] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
