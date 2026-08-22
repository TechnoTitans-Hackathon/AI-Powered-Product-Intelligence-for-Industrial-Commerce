import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.core.db import Base


def generate_uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    """Company / Organization Tenant model for multi-tenant data isolation."""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    industry = Column(String, nullable=True, default="Industrial Manufacturing")
    plan = Column(String, default="enterprise")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """User model associated with a tenant/company."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="specialist")  # admin | specialist | reviewer | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    sku = Column(String, index=True, nullable=True)
    mpn = Column(String, index=True, nullable=True)          # Manufacturer Part Number
    name = Column(String, nullable=False)
    brand = Column(String, index=True, nullable=True)
    manufacturer = Column(String, index=True, nullable=True)
    category = Column(String, index=True, nullable=True)
    subcategory = Column(String, nullable=True)
    industry = Column(String, index=True, nullable=True)
    description = Column(Text, nullable=True)

    # Pipeline scoring (floats stored internally, confidence_level exposed to UI)
    completeness_score = Column(Float, default=0.0)          # 0.0–1.0
    confidence_score = Column(Float, default=0.0)            # 0.0–1.0

    # Qualitative confidence for UI — HIGH / MEDIUM / LOW / CONFLICT
    confidence_level = Column(String, default="LOW")

    # Processing state
    status = Column(String, default="processing", index=True)
    # Values: processing | verified | needs_review | conflicting | failed

    review_status = Column(String, default="PENDING")
    # Values: PENDING | APPROVED | REJECTED | EDITED

    # Missing / conflict counts from Hackathon pipeline
    missing_fields_count = Column(Integer, default=0)
    conflict_fields_count = Column(Integer, default=0)
    fields_total = Column(Integer, default=0)
    fields_populated = Column(Integer, default=0)

    # Full Hackathon ProductIntelligenceResult stored as JSON blob
    intelligence_json = Column(JSON, nullable=True)

    # Commerce output (252-column mapping)
    commerce_json = Column(JSON, nullable=True)

    image_url = Column(String, nullable=True)
    seo_json = Column(JSON, nullable=True)
    raw_input_json = Column(JSON, nullable=True)
    duplicate_candidate_id = Column(String, nullable=True)
    duplicate_match_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attributes = relationship("Attribute", back_populates="product", cascade="all, delete-orphan")
    source_documents = relationship("SourceDocument", back_populates="product", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="product", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationResult", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="product", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="product", cascade="all, delete-orphan")


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    attribute_type = Column(String, default="technical_spec")
    # Values: technical_spec | dimension | material | certification | feature | application
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=True)                     # nullable — missing is valid
    normalized_value = Column(Text, nullable=True)
    unit = Column(String, nullable=True)
    data_type = Column(String, default="string")
    confidence = Column(Float, default=0.0)                 # 0.0–1.0 (Hackathon scale)
    status = Column(String, default="ai_inferred")
    # Values: directly_supported | inferred | missing | conflicting | ai_inferred
    source_snippet = Column(Text, nullable=True)
    source_location = Column(String, nullable=True)
    bbox_json = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    competing_value = Column(Text, nullable=True)           # Conflicting value from other source
    field_status = Column(String, nullable=True)
    # Hackathon FieldStatus: DIRECTLY_SUPPORTED | INFERRED | MISSING | CONFLICTING
    extra_metadata = Column(JSON, nullable=True)

    product = relationship("Product", back_populates="attributes")


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    # Values: pdf | excel | csv | doc | image | text | url | video
    file_size = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    url = Column(String, nullable=True)
    pages = Column(Integer, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    ocr_accuracy = Column(Float, default=100.0)
    provenance_metadata = Column(JSON, nullable=True)

    product = relationship("Product", back_populates="source_documents")
    evidences = relationship("Evidence", back_populates="source_document")


class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    source_document_id = Column(String, ForeignKey("source_documents.id"), nullable=True)
    source_id = Column(String, nullable=True)
    document_name = Column(String, nullable=True)
    url = Column(String, nullable=True)
    page = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    timestamp = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    score = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)
    source_type = Column(String, nullable=True)
    # Hackathon SourceType: MANUFACTURER_DOCUMENT | CATALOG | WEB | KNOWLEDGE_BASE | etc.
    provenance_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="evidences")
    source_document = relationship("SourceDocument", back_populates="evidences")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    status = Column(String, default="QUEUED", index=True)
    # Values: QUEUED | PROCESSING | COMPLETED | FAILED | NEEDS_REVIEW
    step = Column(String, default="INIT")
    pipeline_stage = Column(String, nullable=True)
    # Hackathon stage: DISCOVERING | RETRIEVING | RESEARCHING | ENRICHING | VALIDATING | COMPLETED
    progress = Column(Integer, default=0)                   # 0–100
    ai_mode = Column(String, default="AUTO")
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="jobs")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    severity = Column(String, nullable=False)
    # Values: critical | high | medium | low
    type = Column(String, nullable=False)
    # Values: conflict | missing_field | unit_mismatch | non_standard_name | format_error
    field = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    current_value = Column(Text, nullable=True)             # Renamed from "AI-generated value"
    suggested_value = Column(Text, nullable=True)
    source_a = Column(String, nullable=True)
    source_b = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="validation_issues")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, default="demo", index=True, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    reviewer = Column(String, nullable=False)
    action = Column(String, nullable=False)
    # Values: APPROVED | REJECTED | EDITED
    comment = Column(Text, nullable=True)
    field_name = Column(String, nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="reviews")


class KnowledgeCache(Base):
    __tablename__ = "knowledge_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    indexed_status = Column(Boolean, default=False)
    industry = Column(String, index=True, nullable=True)
    category = Column(String, index=True, nullable=True)
    query_context = Column(Text, nullable=True)
    provenance_metadata = Column(JSON, nullable=True)


class DatasetRecord(Base):
    """Dataset registry entry — permanent baseline and temporary acquired datasets."""
    __tablename__ = "dataset_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    dataset_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    license = Column(String, nullable=False, default="unknown")
    size_bytes = Column(Integer, default=0)
    checksum = Column(String, nullable=True)
    version = Column(String, default="1.0")
    industries = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    description = Column(Text, nullable=True)
    purpose = Column(String, nullable=True)
    permanent = Column(Boolean, default=False)
    status = Column(String, default="active")
    storage_class = Column(String, default="TEMPORARY_ACQUISITION")
    attribution = Column(String, nullable=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


# Official Controlled Knowledge Models
class OfficialManufacturerBrand(Base):
    __tablename__ = "official_manufacturer_brands"

    id = Column(String, primary_key=True, default=generate_uuid)
    manufacturer = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=False)
    normalized_name = Column(String, index=True, nullable=False)


class OfficialLOV(Base):
    __tablename__ = "official_lovs"

    id = Column(String, primary_key=True, default=generate_uuid)
    taxonomy_category = Column(String, index=True, nullable=False)
    attribute_name = Column(String, index=True, nullable=False)
    allowed_value = Column(String, index=True, nullable=False)
    remarks = Column(Text, nullable=True)


class OfficialUOM(Base):
    __tablename__ = "official_uoms"

    id = Column(String, primary_key=True, default=generate_uuid)
    standard_unit = Column(String, index=True, nullable=False)
    abbreviation = Column(String, index=True, nullable=False)
    allowed_synonyms = Column(JSON, nullable=True)
    conversion_factor = Column(Float, default=1.0)


class OfficialDecimalFraction(Base):
    __tablename__ = "official_decimal_fractions"

    id = Column(String, primary_key=True, default=generate_uuid)
    fraction = Column(String, index=True, nullable=False)
    decimal_value = Column(Float, nullable=False)
    standard_representation = Column(String, nullable=False)


class AITraceLog(Base):
    """Permanent storage for Live AI Pipeline Trace events."""
    __tablename__ = "ai_trace_logs"

    id = Column(String, primary_key=True)  # event_id
    trace_id = Column(String, index=True, nullable=False)
    request_id = Column(String, index=True, nullable=True)
    job_id = Column(String, index=True, nullable=True)
    product_id = Column(String, index=True, nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=True)
    sequence = Column(Integer, nullable=False)
    parent_event_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    stage = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    component = Column(String, nullable=True)
    status = Column(String, nullable=False)
    metrics_json = Column(JSON, nullable=True)
    payload_json = Column(JSON, nullable=True)

