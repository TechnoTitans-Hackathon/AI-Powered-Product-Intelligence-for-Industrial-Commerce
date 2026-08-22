from backend.core.db import Base
# Import all models here for SQLAlchemy metadata recognition
from backend.db.models import (
    Tenant,
    User,
    Product,
    Attribute,
    SourceDocument,
    Evidence,
    ProcessingJob,
    ValidationResult,
    HumanReview,
    KnowledgeCache,
    OfficialManufacturerBrand,
    OfficialLOV,
    OfficialUOM,
    OfficialDecimalFraction
)
