from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.db.models import Product, Attribute, SourceDocument, Evidence, ValidationResult
from backend.schemas.product import ProductCreate, ProductUpdate
from backend.integration.output_adapter import map_confidence_level
from backend.core.logging import logger


class ProductService:
    """
    Manages product lifecycle, persistence, tenant isolation, and schema transformations.
    Converts database entities into clean API responses suitable for frontend consumption.
    """

    def create_product(
        self,
        db: Session,
        payload: ProductCreate,
        extra_attributes: Optional[Dict[str, Any]] = None,
        tenant_id: str = "demo"
    ) -> Product:
        db_product = Product(
            tenant_id=tenant_id,
            name=payload.name,
            sku=payload.sku,
            mpn=payload.mpn or payload.sku,
            brand=payload.brand or "Unknown",
            manufacturer=payload.manufacturer or "Unknown",
            category=payload.category or "General Industrial",
            subcategory=payload.subcategory or "",
            industry=payload.industry or "Industrial",
            description=payload.description or f"Industrial product: {payload.name}",
            image_url=payload.imageUrl or "",
            completeness_score=0.0,
            confidence_score=0.0,
            confidence_level="LOW",
            status="processing",
            review_status="PENDING",
            raw_input_json=payload.model_dump()
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        # Preserve unmapped/extra catalog columns as initial dynamic attributes
        if extra_attributes:
            for k, v in extra_attributes.items():
                if v is not None:
                    db_attr = Attribute(
                        tenant_id=tenant_id,
                        product_id=db_product.id,
                        attribute_type="technical_spec",
                        key=str(k),
                        value=str(v),
                        normalized_value=str(v),
                        confidence=0.5,
                        status="raw_imported",
                        field_status="DIRECTLY_SUPPORTED",
                        source_location="Spreadsheet Catalog",
                    )
                    db.add(db_attr)
            db.commit()
            db.refresh(db_product)

        logger.info(f"Created product ID: {db_product.id}, Name: {db_product.name}, Tenant: {tenant_id}")
        return db_product

    def get_product(self, db: Session, product_id: str, tenant_id: Optional[str] = None) -> Optional[Product]:
        query = db.query(Product).filter(Product.id == product_id)
        if tenant_id:
            query = query.filter(Product.tenant_id == tenant_id)
        return query.first()

    def list_products(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        confidence_level: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Product]:
        query = db.query(Product)

        if tenant_id:
            query = query.filter(Product.tenant_id == tenant_id)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.sku.ilike(search_pattern),
                    Product.mpn.ilike(search_pattern),
                    Product.brand.ilike(search_pattern),
                    Product.manufacturer.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )

        if category and category != "All":
            query = query.filter(Product.category.ilike(f"%{category}%"))

        if status and status != "All":
            query = query.filter(Product.status == status.lower())

        if confidence_level and confidence_level != "All":
            query = query.filter(Product.confidence_level == confidence_level.upper())

        return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()

    def update_product(self, db: Session, product_id: str, payload: ProductUpdate, tenant_id: Optional[str] = None) -> Optional[Product]:
        product = self.get_product(db, product_id, tenant_id=tenant_id)
        if not product:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if hasattr(product, key) and val is not None:
                setattr(product, key, val)

        db.commit()
        db.refresh(product)
        return product

    def delete_product(self, db: Session, product_id: str, tenant_id: Optional[str] = None) -> bool:
        product = self.get_product(db, product_id, tenant_id=tenant_id)
        if not product:
            return False
        db.delete(product)
        db.commit()
        return True

    def format_to_response(self, product: Product) -> Dict[str, Any]:
        """
        Formats SQLAlchemy Product model into clean ProductResponse dict matching frontend DTOs.
        Uses dynamic attributes and qualitative confidence indicators.
        Robustly parses stored intelligence_json if present.
        """
        technical_specs = []
        dimensions = []
        materials = []
        certifications = []
        features = []
        applications = []
        dynamic_attributes = []

        field_name_dim_keywords = {"dimension", "dimensions", "length", "width", "height", "diameter", "bore", "weight", "thickness", "size"}
        field_name_mat_keywords = {"material", "materials", "construction", "body material", "housing material"}
        field_name_cert_keywords = {"certification", "certifications", "standards", "approvals", "compliance", "standards/approvals"}
        field_name_app_keywords = {"application", "applications", "intended use", "use case"}

        # 1. Process relational Product.attributes
        for attr in product.attributes:
            field_conf = map_confidence_level(attr.confidence) if attr.confidence else "LOW"
            attr_dict = {
                "id": attr.id,
                "key": attr.key,
                "value": attr.value,
                "normalizedValue": attr.normalized_value or attr.value,
                "unit": attr.unit or "",
                "confidence": attr.confidence,
                "confidenceLevel": field_conf,
                "status": attr.status or "ai_inferred",
                "fieldStatus": attr.field_status or ("DIRECTLY_SUPPORTED" if attr.value else "MISSING"),
                "sourceSnippet": attr.source_snippet or "",
                "sourceLocation": attr.source_location or "",
                "explanation": attr.explanation or "",
                "competingValue": attr.competing_value,
                "attributeType": attr.attribute_type or "technical_spec"
            }

            dynamic_attributes.append(attr_dict)
            key_lower = attr.key.lower()

            if attr.attribute_type == "dimension" or any(k in key_lower for k in field_name_dim_keywords):
                dimensions.append({
                    "id": attr.id,
                    "parameter": attr.key,
                    "value": attr.value or "",
                    "unit": attr.unit or "",
                    "normalizedValue": attr.normalized_value or attr.value or "",
                    "confidence": attr.confidence,
                    "confidenceLevel": field_conf,
                    "status": attr.status or "ai_inferred",
                    "sourceSnippet": attr.source_snippet or "",
                    "sourceLocation": attr.source_location or "",
                    "explanation": attr.explanation or ""
                })
            elif attr.attribute_type == "material" or any(k in key_lower for k in field_name_mat_keywords):
                materials.append({
                    "id": attr.id,
                    "parameter": attr.key,
                    "value": attr.value or "",
                    "confidence": attr.confidence,
                    "confidenceLevel": field_conf,
                    "status": attr.status or "verified",
                    "sourceSnippet": attr.source_snippet or "",
                    "explanation": attr.explanation or ""
                })
            elif attr.attribute_type == "certification" or any(k in key_lower for k in field_name_cert_keywords):
                certifications.append({
                    "id": attr.id,
                    "parameter": attr.key,
                    "value": attr.value or "",
                    "confidence": attr.confidence,
                    "confidenceLevel": field_conf,
                    "status": attr.status or "verified",
                    "sourceSnippet": attr.source_snippet or "",
                    "explanation": attr.explanation or ""
                })
            elif attr.attribute_type == "feature":
                features.append({
                    "id": attr.id,
                    "value": attr.value or "",
                    "confidence": attr.confidence,
                    "confidenceLevel": field_conf,
                    "explanation": attr.explanation or ""
                })
            elif attr.attribute_type == "application" or any(k in key_lower for k in field_name_app_keywords):
                applications.append({
                    "id": attr.id,
                    "value": attr.value or "",
                    "confidence": attr.confidence,
                    "confidenceLevel": field_conf,
                    "explanation": attr.explanation or ""
                })
            else:
                technical_specs.append(attr_dict)

        # 2. Extract from intelligence_json if relational tables don't have them
        if product.intelligence_json and isinstance(product.intelligence_json, dict):
            intel = product.intelligence_json
            
            # Attributes from JSON
            if not dynamic_attributes and intel.get("attributes"):
                for attr_item in intel.get("attributes", []):
                    field_name = attr_item.get("field_name", "")
                    val = attr_item.get("value")
                    unit = attr_item.get("unit") or ""
                    conf = attr_item.get("confidence", 0.0)
                    field_status = attr_item.get("status") or ("DIRECTLY_SUPPORTED" if val else "MISSING")
                    field_conf = map_confidence_level(conf)

                    ev_snippet = ""
                    ev_loc = ""
                    if attr_item.get("evidence"):
                        first_ev = attr_item["evidence"][0]
                        ev_snippet = first_ev.get("snippet") or first_ev.get("content") or ""
                        ev_loc = first_ev.get("source") or ""

                    d_attr = {
                        "id": f"json_attr_{field_name}",
                        "key": field_name,
                        "value": val,
                        "normalizedValue": attr_item.get("normalized_value") or val,
                        "unit": unit,
                        "confidence": conf,
                        "confidenceLevel": field_conf,
                        "status": "ai_inferred",
                        "fieldStatus": field_status,
                        "sourceSnippet": ev_snippet,
                        "sourceLocation": ev_loc,
                        "explanation": attr_item.get("reason") or "",
                        "competingValue": None,
                        "attributeType": "technical_spec",
                    }
                    dynamic_attributes.append(d_attr)
                    
                    fn_lower = field_name.lower()
                    if any(k in fn_lower for k in field_name_dim_keywords):
                        dimensions.append({
                            "id": d_attr["id"],
                            "parameter": field_name,
                            "value": val or "",
                            "unit": unit,
                            "normalizedValue": val or "",
                            "confidence": conf,
                            "confidenceLevel": field_conf,
                            "status": "ai_inferred",
                            "sourceSnippet": ev_snippet,
                            "sourceLocation": ev_loc,
                            "explanation": attr_item.get("reason") or "",
                        })
                    elif any(k in fn_lower for k in field_name_mat_keywords):
                        materials.append({
                            "id": d_attr["id"],
                            "parameter": field_name,
                            "value": val or "",
                            "confidence": conf,
                            "confidenceLevel": field_conf,
                            "status": "verified",
                            "sourceSnippet": ev_snippet,
                            "explanation": attr_item.get("reason") or "",
                        })
                    elif any(k in fn_lower for k in field_name_cert_keywords):
                        certifications.append({
                            "id": d_attr["id"],
                            "parameter": field_name,
                            "value": val or "",
                            "confidence": conf,
                            "confidenceLevel": field_conf,
                            "status": "verified",
                            "sourceSnippet": ev_snippet,
                            "explanation": attr_item.get("reason") or "",
                        })
                    elif any(k in fn_lower for k in field_name_app_keywords):
                        applications.append({
                            "id": d_attr["id"],
                            "value": val or "",
                            "confidence": conf,
                            "confidenceLevel": field_conf,
                            "explanation": attr_item.get("reason") or "",
                        })
                    else:
                        technical_specs.append(d_attr)

            # Features from JSON
            if not features and intel.get("features"):
                for feat in intel.get("features", []):
                    features.append({
                        "id": f"feat_{len(features)+1}",
                        "value": feat.get("value") or "",
                        "confidence": feat.get("confidence", 0.8),
                        "confidenceLevel": map_confidence_level(feat.get("confidence", 0.8)),
                        "explanation": feat.get("reason") or ""
                    })

        # 3. Validation issues
        validation_issues = []
        for issue in product.validation_issues:
            validation_issues.append({
                "id": issue.id,
                "severity": issue.severity,
                "type": issue.type,
                "field": issue.field,
                "message": issue.message,
                "currentValue": issue.current_value,
                "suggestedValue": issue.suggested_value,
                "sourceA": issue.source_a,
                "sourceB": issue.source_b,
                "resolved": issue.resolved,
                "createdAt": issue.created_at.isoformat() if issue.created_at else None
            })

        # 4. Source document
        source_doc = None
        if product.source_documents:
            sd = product.source_documents[0]
            source_doc = {
                "id": sd.id,
                "name": sd.name,
                "type": sd.type,
                "fileSize": sd.file_size or "1.2 MB",
                "url": sd.url or "",
                "pages": sd.pages or 1,
                "extractedAt": sd.extracted_at.isoformat() if sd.extracted_at else "",
                "ocrAccuracy": sd.ocr_accuracy
            }

        # Qualitative confidence
        qualitative_conf = product.confidence_level or map_confidence_level(
            product.confidence_score, product.conflict_fields_count or 0
        )

        # Dynamic fields count
        total_fields = product.fields_total or len(dynamic_attributes) or 10
        pop_fields = product.fields_populated or len([a for a in dynamic_attributes if a.get("value")]) or 0
        miss_fields = product.missing_fields_count or (total_fields - pop_fields if total_fields > pop_fields else 0)

        return {
            "id": product.id,
            "tenantId": product.tenant_id,
            "sku": product.sku or product.mpn or "",
            "mpn": product.mpn or product.sku or "",
            "name": product.name,
            "brand": product.brand or "Unknown",
            "manufacturer": product.manufacturer or "Unknown",
            "category": product.category or "General",
            "subcategory": product.subcategory or "",
            "industry": product.industry or "Industrial",
            "description": product.description or "",
            "completenessScore": product.completeness_score,
            "confidenceScore": product.confidence_score,
            "confidenceLevel": qualitative_conf,
            "status": product.status,
            "review_status": product.review_status,
            "missingFieldsCount": miss_fields,
            "conflictFieldsCount": product.conflict_fields_count or 0,
            "fieldsTotal": total_fields,
            "fieldsPopulated": pop_fields,
            "sourceDocument": source_doc,
            "imageUrl": product.image_url or "",
            "technicalSpecs": technical_specs,
            "dimensions": dimensions,
            "materials": materials,
            "certifications": certifications,
            "features": features,
            "applications": applications,
            "dynamicAttributes": dynamic_attributes,
            "compatibility": [],
            "seo": {
                "title": f"{product.name} | {product.brand}",
                "metaDescription": product.description or "",
                "keywords": [k for k in [product.brand, product.category, product.sku] if k]
            },
            "images": [product.image_url] if product.image_url else [],
            "duplicateCandidateId": product.duplicate_candidate_id,
            "duplicateMatchScore": product.duplicate_match_score,
            "validationIssues": validation_issues,
            "intelligence": product.intelligence_json,
            "commerceData": product.commerce_json,
            "createdAt": product.created_at.isoformat() if product.created_at else None,
            "updatedAt": product.updated_at.isoformat() if product.updated_at else None
        }


product_service = ProductService()
