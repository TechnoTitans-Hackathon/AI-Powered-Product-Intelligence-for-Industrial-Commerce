import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.db.models import KnowledgeCache
from backend.core.storage_safety import storage_safety
from backend.core.logging import logger

class CacheManager:
    """
    Manages temporary knowledge cache lifecycle:
    1. Prevents duplicate downloads via URL/file hash/source_id checks.
    2. Registers temporary sources with expiration timestamps (default: 7 days after last use).
    3. Enforces 4 GB ceiling before caching new downloads.
    4. Deletes expired files, extracted data, chunks, and embeddings while preserving provenance records.
    5. Supports industry/category/query_context for multi-industry filtering.
    """

    @staticmethod
    def calculate_hash(content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def get_cached_item_by_hash(self, db: Session, file_hash: str) -> Optional[KnowledgeCache]:
        item = db.query(KnowledgeCache).filter(KnowledgeCache.file_hash == file_hash).first()
        if item:
            # Refresh last used timestamp and expiry (7 days from NOW)
            item.last_used_at = datetime.utcnow()
            item.expires_at = datetime.utcnow() + timedelta(days=storage_safety.retention_days)
            db.commit()
            db.refresh(item)
        return item

    def get_cached_item_by_url(self, db: Session, url: str) -> Optional[KnowledgeCache]:
        item = db.query(KnowledgeCache).filter(KnowledgeCache.url == url).first()
        if item:
            item.last_used_at = datetime.utcnow()
            item.expires_at = datetime.utcnow() + timedelta(days=storage_safety.retention_days)
            db.commit()
            db.refresh(item)
        return item

    def get_cached_item_by_source_id(self, db: Session, source_id: str) -> Optional[KnowledgeCache]:
        item = db.query(KnowledgeCache).filter(KnowledgeCache.source_id == source_id).first()
        if item:
            item.last_used_at = datetime.utcnow()
            item.expires_at = datetime.utcnow() + timedelta(days=storage_safety.retention_days)
            db.commit()
            db.refresh(item)
        return item

    def register_cache_item(
        self,
        db: Session,
        source_id: str,
        file_name: str,
        file_bytes: bytes,
        file_type: str,
        url: Optional[str] = None,
        provenance_metadata: Optional[Dict[str, Any]] = None,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        query_context: Optional[str] = None,
    ) -> KnowledgeCache:
        file_size = len(file_bytes)
        file_hash = self.calculate_hash(file_bytes)

        # Enforce 4 GB capacity check before registering
        storage_safety.check_and_evict_cache(db, required_bytes=file_size)

        now = datetime.utcnow()
        expires_at = now + timedelta(days=storage_safety.retention_days)

        # Extract industry/category from provenance if not provided directly
        prov = provenance_metadata or {}
        if not industry:
            industry = prov.get("industry", "")
        if not category:
            category = prov.get("category", "")
        if not query_context:
            query_context = prov.get("acquired_for_query", "")

        cache_entry = KnowledgeCache(
            source_id=source_id,
            url=url,
            file_name=file_name,
            file_hash=file_hash,
            file_type=file_type,
            file_size_bytes=file_size,
            downloaded_at=now,
            last_used_at=now,
            expires_at=expires_at,
            indexed_status=True,
            industry=industry,
            category=category,
            query_context=query_context,
            provenance_metadata=prov,
        )
        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)
        logger.info(f"Registered temporary cache item {source_id} (hash: {file_hash[:8]}...), expires at {expires_at}")
        return cache_entry

    def cleanup_expired(self, db: Session) -> int:
        now = datetime.utcnow()
        expired_entries = db.query(KnowledgeCache).filter(KnowledgeCache.expires_at < now).all()
        freed_bytes = 0

        for entry in expired_entries:
            freed_bytes += entry.file_size_bytes
            # Remove raw file if exists
            target_path = os.path.join(storage_safety.temp_cache_dir, entry.file_name)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception as e:
                    logger.error(f"Error removing raw temp file {target_path}: {e}")

            # Keep provenance record in DB by resetting file status rather than hard deleting the row
            entry.indexed_status = False
            logger.info(f"Cleaned up expired cache item {entry.source_id}. Provenance retained.")

        db.commit()
        return freed_bytes

    def evict_lru(self, db: Session, required_bytes: int) -> int:
        """
        Evict least-recently-used temporary cache items to free space.
        Returns total bytes freed.
        NEVER evicts permanent baseline knowledge.
        """
        items = (
            db.query(KnowledgeCache)
            .filter(KnowledgeCache.indexed_status == True)
            .order_by(KnowledgeCache.last_used_at.asc())
            .all()
        )

        freed_bytes = 0
        for item in items:
            if freed_bytes >= required_bytes:
                break

            # Remove file from temp cache
            target_path = os.path.join(storage_safety.temp_cache_dir, item.file_name)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                    logger.info(f"LRU evicted cache file: {target_path} ({item.file_size_bytes} bytes)")
                except Exception as e:
                    logger.error(f"Failed to evict {target_path}: {e}")
                    continue

            freed_bytes += item.file_size_bytes
            # Preserve provenance record
            item.indexed_status = False

        db.commit()
        return freed_bytes

    def get_cache_statistics(self, db: Session) -> Dict[str, Any]:
        """Return statistics about the temporary knowledge cache."""
        all_items = db.query(KnowledgeCache).all()
        active_items = [i for i in all_items if i.indexed_status]
        expired_items = [i for i in all_items if not i.indexed_status]

        return {
            "total_items": len(all_items),
            "active_items": len(active_items),
            "expired_provenance_records": len(expired_items),
            "total_active_bytes": sum(i.file_size_bytes for i in active_items),
            "industries_covered": list(set(i.industry for i in active_items if i.industry)),
            "categories_covered": list(set(i.category for i in active_items if i.category)),
        }

cache_manager = CacheManager()
