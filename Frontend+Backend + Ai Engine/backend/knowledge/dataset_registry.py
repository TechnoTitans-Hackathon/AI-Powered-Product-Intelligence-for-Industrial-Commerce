import hashlib
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.db.models import DatasetRecord
from backend.core.logging import logger


class DatasetRegistryService:
    """
    Manages the dataset registry for both permanent baseline and temporary
    acquired datasets. Every dataset entry records source, license, size,
    checksum, industries, and provenance.
    """

    def register(
        self,
        db: Session,
        dataset_id: str,
        name: str,
        source: str,
        license: str,
        size_bytes: int,
        permanent: bool,
        source_url: str = "",
        checksum: str = "",
        version: str = "1.0",
        industries: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        description: str = "",
        purpose: str = "",
        status: str = "active",
        attribution: str = ""
    ) -> DatasetRecord:
        """Register a new dataset. Checks for duplicates first."""
        existing = self.get_by_id(db, dataset_id)
        if existing:
            logger.info(f"Dataset '{dataset_id}' already registered. Skipping.")
            return existing

        storage_class = "PERMANENT_BASELINE" if permanent else "TEMPORARY_ACQUISITION"

        record = DatasetRecord(
            dataset_id=dataset_id,
            name=name,
            source=source,
            source_url=source_url,
            license=license,
            size_bytes=size_bytes,
            checksum=checksum,
            version=version,
            industries=industries or [],
            categories=categories or [],
            description=description,
            purpose=purpose,
            permanent=permanent,
            status=status,
            storage_class=storage_class,
            attribution=attribution
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Registered dataset: {dataset_id} (permanent={permanent}, {size_bytes} bytes)")
        return record

    def get_by_id(self, db: Session, dataset_id: str) -> Optional[DatasetRecord]:
        return db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).first()

    def list_all(self, db: Session) -> List[DatasetRecord]:
        return db.query(DatasetRecord).all()

    def list_permanent(self, db: Session) -> List[DatasetRecord]:
        return db.query(DatasetRecord).filter(DatasetRecord.permanent == True).all()

    def list_temporary(self, db: Session) -> List[DatasetRecord]:
        return db.query(DatasetRecord).filter(DatasetRecord.permanent == False).all()

    def get_by_industry(self, db: Session, industry: str) -> List[DatasetRecord]:
        """Find datasets relevant to a specific industry."""
        # JSON column search — SQLite compatible via string matching
        return db.query(DatasetRecord).filter(
            DatasetRecord.industries.contains(industry)
        ).all()

    def check_duplicate(self, db: Session, checksum: str) -> Optional[DatasetRecord]:
        """Check if a dataset with the same checksum already exists."""
        if not checksum:
            return None
        return db.query(DatasetRecord).filter(DatasetRecord.checksum == checksum).first()

    def check_license(self, license_str: str) -> Dict[str, Any]:
        """
        Evaluate whether a license permits the intended use.
        Returns a status dict. Does NOT make a legal determination —
        just flags known open licenses vs unknown ones.
        """
        permissive_licenses = {
            "cc0", "cc0-1.0", "public domain", "cc-by", "cc-by-4.0",
            "cc-by-sa", "cc-by-sa-4.0", "mit", "apache-2.0", "bsd",
            "odc-by", "odc-odbl", "pddl", "curated-reference",
        }
        normalized = license_str.strip().lower()
        if normalized in permissive_licenses:
            return {"permitted": True, "license": license_str, "review_required": False}
        else:
            return {"permitted": False, "license": license_str, "review_required": True}

    def get_total_size(self, db: Session, permanent_only: bool = False) -> int:
        """Get total size of all registered datasets."""
        query = db.query(DatasetRecord)
        if permanent_only:
            query = query.filter(DatasetRecord.permanent == True)
        records = query.all()
        return sum(r.size_bytes for r in records)

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


dataset_registry = DatasetRegistryService()
