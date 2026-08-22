import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.db.models import Product, ValidationResult, Attribute
from backend.knowledge.official_knowledge import official_knowledge_service
from backend.schemas.validation import ValidationResponse, ValidationCheckResult
from backend.core.logging import logger

class ValidationService:
    """
    Deterministic Validator.
    Runs rules independently of AI reasoning to ensure data integrity,
    UOM compliance, LOV verification, and conflict detection.
    """

    def validate_product(self, db: Session, product: Product) -> ValidationResponse:
        errors = []
        warnings = []
        checks = []
        issues = []

        # 1. Required Core Fields Check
        req_passed = True
        missing_fields = []
        if not product.name or len(product.name.strip()) < 3:
            missing_fields.append("name")
            req_passed = False
        if not product.brand:
            missing_fields.append("brand")
            req_passed = False

        if req_passed:
            checks.append(ValidationCheckResult(check_name="Required Core Fields", passed=True, details="Name and brand present."))
        else:
            checks.append(ValidationCheckResult(check_name="Required Core Fields", passed=False, details=f"Missing core fields: {', '.join(missing_fields)}"))
            errors.append(f"Missing required core fields: {', '.join(missing_fields)}")
            issues.append({
                "id": str(uuid.uuid4()),
                "severity": "critical",
                "type": "missing_field",
                "field": missing_fields[0],
                "message": f"Core required field '{missing_fields[0]}' is missing."
            })

        # 2. Manufacturer & Brand Official Lookup
        if product.brand:
            mfg_info = official_knowledge_service.lookup_manufacturer_brand(db, product.brand)
            if mfg_info:
                checks.append(ValidationCheckResult(check_name="Official Brand Verification", passed=True, details=f"Brand '{product.brand}' verified under manufacturer '{mfg_info['manufacturer']}'."))
            else:
                checks.append(ValidationCheckResult(check_name="Official Brand Verification", passed=False, details=f"Brand '{product.brand}' not found in official UniCat master list."))
                warnings.append(f"Unverified brand name: '{product.brand}'.")
                issues.append({
                    "id": str(uuid.uuid4()),
                    "severity": "medium",
                    "type": "non_standard_name",
                    "field": "brand",
                    "message": f"Brand '{product.brand}' is not listed in the official UniCat Manufacturer/Brand master."
                })

        # 3. UOM Standard Checks
        uom_passed = True
        for attr in product.attributes:
            if attr.unit:
                uom_match = official_knowledge_service.normalize_uom(db, attr.unit)
                if not uom_match:
                    uom_passed = False
                    warnings.append(f"Non-standard UOM unit '{attr.unit}' in attribute '{attr.key}'.")
                    issues.append({
                        "id": str(uuid.uuid4()),
                        "severity": "low",
                        "type": "unit_mismatch",
                        "field": attr.key,
                        "message": f"Unit '{attr.unit}' for attribute '{attr.key}' does not match official UOM standards."
                    })

        checks.append(ValidationCheckResult(
            check_name="UOM Standard Units",
            passed=uom_passed,
            details="All attribute units conform to official UOM master." if uom_passed else "Some attribute units are non-standard."
        ))

        # 4. Duplicate SKU Check
        if product.sku:
            duplicate = db.query(Product).filter(
                Product.sku == product.sku,
                Product.id != product.id
            ).first()
            if duplicate:
                product.duplicate_candidate_id = duplicate.id
                product.duplicate_match_score = 99.0
                errors.append(f"Duplicate SKU '{product.sku}' matches product ID {duplicate.id}.")
                issues.append({
                    "id": str(uuid.uuid4()),
                    "severity": "high",
                    "type": "duplicate",
                    "field": "sku",
                    "message": f"Exact duplicate SKU '{product.sku}' detected.",
                    "sourceA": product.id,
                    "sourceB": duplicate.id
                })
                checks.append(ValidationCheckResult(check_name="Duplicate Detection", passed=False, details=f"Duplicate SKU detected matching product {duplicate.id}"))
            else:
                checks.append(ValidationCheckResult(check_name="Duplicate Detection", passed=True, details="No duplicate SKU found."))

        # 5. Conflicting Values Check
        conflicts = [a for a in product.attributes if a.competing_value]
        if conflicts:
            for c in conflicts:
                warnings.append(f"Competing values for attribute '{c.key}': '{c.value}' vs '{c.competing_value}'.")
                issues.append({
                    "id": str(uuid.uuid4()),
                    "severity": "high",
                    "type": "conflict",
                    "field": c.key,
                    "message": f"Conflicting values detected for attribute '{c.key}'.",
                    "sourceA": c.value,
                    "sourceB": c.competing_value
                })
            checks.append(ValidationCheckResult(check_name="Cross-Source Conflict Check", passed=False, details=f"Detected {len(conflicts)} conflicting attribute values."))
        else:
            checks.append(ValidationCheckResult(check_name="Cross-Source Conflict Check", passed=True, details="No attribute conflicts detected."))

        # Calculate Validation Score & Overall Status
        if errors:
            status = "FAILED"
            score = 40.0
        elif warnings or conflicts:
            status = "NEEDS_REVIEW"
            score = 75.0
        else:
            status = "PASS"
            score = 98.0

        # Persist validation issues in DB
        db.query(ValidationResult).filter(ValidationResult.product_id == product.id).delete()
        for iss in issues:
            db_issue = ValidationResult(
                product_id=product.id,
                severity=iss["severity"],
                type=iss["type"],
                field=iss["field"],
                message=iss["message"],
                source_a=iss.get("sourceA"),
                source_b=iss.get("sourceB")
            )
            db.add(db_issue)

        db.commit()

        logger.info(f"Validated product {product.id}: Status={status}, Score={score}")
        return ValidationResponse(
            product_id=product.id,
            status=status,
            score=score,
            errors=errors,
            warnings=warnings,
            checks=checks,
            validation_issues=issues
        )

validation_service = ValidationService()
