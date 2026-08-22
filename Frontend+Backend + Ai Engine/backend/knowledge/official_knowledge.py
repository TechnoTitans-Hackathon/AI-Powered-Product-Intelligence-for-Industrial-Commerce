from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.db.models import (
    OfficialManufacturerBrand,
    OfficialLOV,
    OfficialUOM,
    OfficialDecimalFraction
)
from backend.core.logging import logger

class OfficialKnowledgeService:
    """
    Service for official controlled challenge knowledge lookups:
    - Manufacturer + Brand Master
    - UniCat LOV (Taxonomy & Allowed Values)
    - UOM Standards & Abbreviations
    - Decimal & Fraction conversions
    - 200-Item Input vs Output Reference
    """

    def lookup_manufacturer_brand(self, db: Session, query: str) -> Optional[Dict[str, str]]:
        q_norm = query.strip().lower()
        match = db.query(OfficialManufacturerBrand).filter(
            OfficialManufacturerBrand.normalized_name == q_norm
        ).first()
        if not match:
            # Fuzzy / contains lookup fallback
            match = db.query(OfficialManufacturerBrand).filter(
                OfficialManufacturerBrand.brand.ilike(f"%{query}%")
            ).first()

        if match:
            return {
                "manufacturer": match.manufacturer,
                "brand": match.brand,
                "normalized_name": match.normalized_name
            }
        return None

    def lookup_lov(self, db: Session, category: str, attribute_name: str, value: str) -> bool:
        match = db.query(OfficialLOV).filter(
            OfficialLOV.taxonomy_category.ilike(category),
            OfficialLOV.attribute_name.ilike(attribute_name),
            OfficialLOV.allowed_value.ilike(value)
        ).first()
        return match is not None

    def get_allowed_lov_values(self, db: Session, category: str, attribute_name: str) -> List[str]:
        rows = db.query(OfficialLOV).filter(
            OfficialLOV.taxonomy_category.ilike(category),
            OfficialLOV.attribute_name.ilike(attribute_name)
        ).all()
        return [r.allowed_value for r in rows]

    def normalize_uom(self, db: Session, raw_uom: str) -> Optional[Dict[str, Any]]:
        raw_clean = raw_uom.strip()
        uoms = db.query(OfficialUOM).all()
        for u in uoms:
            synonyms = u.allowed_synonyms or []
            if raw_clean.lower() in [s.lower() for s in synonyms] or raw_clean == u.abbreviation:
                return {
                    "standard_unit": u.standard_unit,
                    "abbreviation": u.abbreviation,
                    "conversion_factor": u.conversion_factor
                }
        return None

    def convert_fraction_to_decimal(self, db: Session, fraction_str: str) -> Optional[Dict[str, Any]]:
        clean_frac = fraction_str.strip().replace('"', '').replace('in', '').strip()
        match = db.query(OfficialDecimalFraction).filter(
            OfficialDecimalFraction.fraction == clean_frac
        ).first()
        if match:
            return {
                "fraction": match.fraction,
                "decimal_value": match.decimal_value,
                "standard_representation": match.standard_representation
            }
        return None

official_knowledge_service = OfficialKnowledgeService()
