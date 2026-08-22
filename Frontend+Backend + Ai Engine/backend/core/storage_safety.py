import os
import shutil
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.logging import logger

class StorageSafetyManager:
    """
    Enforces storage safety constraints:
    1. Tracks storage usage across Permanent Knowledge, Temp Cache, and User Uploads.
    2. Enforces 4 GB maximum cache size for downloaded temporary knowledge.
    3. Handles LRU eviction when temporary cache approaches or exceeds capacity.
    4. Handles 7-day retention expiry for temporary cache.
    5. NEVER deletes permanent baseline knowledge or user-uploaded source files.
    """

    def __init__(
        self,
        max_permanent_bytes: int = settings.MAX_PERMANENT_SIZE_BYTES,
        max_temp_bytes: int = settings.MAX_TEMP_CACHE_SIZE_BYTES,
        retention_days: int = settings.CACHE_RETENTION_DAYS,
        temp_cache_dir: str = settings.TEMP_CACHE_PATH
    ):
        self.max_permanent_bytes = max_permanent_bytes
        self.max_temp_bytes = max_temp_bytes
        self.retention_days = retention_days
        self.temp_cache_dir = temp_cache_dir

    def get_directory_size(self, path: str) -> int:
        total_size = 0
        if not os.path.exists(path):
            return 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def get_storage_stats(self) -> dict:
        perm_size = self.get_directory_size(settings.PERMANENT_KNOWLEDGE_PATH)
        temp_size = self.get_directory_size(settings.TEMP_CACHE_PATH)
        
        # We also need dataset counts. We can get them from dataset registry, but to avoid circular imports, 
        # let's import it locally or assume the caller handles merging stats if needed.
        # Actually, the user requirement for `storage-stats` requires exact keys:
        # permanent_bytes, permanent_limit_bytes, permanent_used_percent,
        # temporary_bytes, temporary_limit_bytes, temporary_used_percent,
        # total_knowledge_bytes, total_knowledge_limit_bytes, dataset_count, etc.
        # We will just return the size stats here and let the endpoint add dataset counts.
        
        return {
            "permanent_bytes": perm_size,
            "permanent_limit_bytes": self.max_permanent_bytes,
            "permanent_used_percent": round((perm_size / self.max_permanent_bytes) * 100, 2) if self.max_permanent_bytes > 0 else 0,
            "permanent_target_bytes": int(self.max_permanent_bytes * 0.75), # e.g. 1.5 GiB target
            "permanent_actual_bytes": perm_size,
            "temporary_bytes": temp_size,
            "temporary_limit_bytes": self.max_temp_bytes,
            "temporary_used_percent": round((temp_size / self.max_temp_bytes) * 100, 2) if self.max_temp_bytes > 0 else 0,
            "total_knowledge_bytes": perm_size + temp_size,
            "total_knowledge_limit_bytes": self.max_permanent_bytes + self.max_temp_bytes
        }

    def check_permanent_storage(self, required_bytes: int = 0) -> bool:
        """Enforces 2 GiB maximum for permanent knowledge."""
        perm_size = self.get_directory_size(settings.PERMANENT_KNOWLEDGE_PATH)
        if perm_size + required_bytes <= self.max_permanent_bytes:
            return True
        logger.warning(
            f"Permanent storage ({perm_size} bytes) + required ({required_bytes} bytes) "
            f"exceeds max limit ({self.max_permanent_bytes} bytes). Rejected."
        )
        return False

    def check_and_evict_cache(self, db: Session, required_bytes: int = 0) -> bool:
        """
        Evicts temporary cache files if current size + required_bytes exceeds max_temp_bytes.
        """
        temp_size = self.get_directory_size(self.temp_cache_dir)
        
        if temp_size + required_bytes <= self.max_temp_bytes:
            return True

        logger.warning(
            f"Temporary storage ({temp_size} bytes) + required ({required_bytes} bytes) "
            f"exceeds max limit ({self.max_temp_bytes} bytes). Initiating LRU eviction..."
        )

        target_eviction_bytes = (temp_size + required_bytes) - self.max_temp_bytes
        
        from backend.knowledge.cache_manager import cache_manager
        freed_bytes = cache_manager.evict_lru(db, required_bytes=target_eviction_bytes)
        logger.info(f"LRU eviction completed. Freed {freed_bytes} bytes.")

        # Re-check after eviction
        new_temp_size = self.get_directory_size(self.temp_cache_dir)
        return new_temp_size + required_bytes <= self.max_temp_bytes

    def cleanup_expired_cache(self) -> int:
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff.timestamp()
        freed_bytes = 0

        for root, _, filenames in os.walk(self.temp_cache_dir):
            for f in filenames:
                filepath = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(filepath)
                    if mtime < cutoff_timestamp:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        freed_bytes += size
                        logger.info(f"Expired cache item removed: {filepath} ({size} bytes)")
                except Exception as e:
                    logger.error(f"Error checking/deleting file {filepath}: {e}")

        return freed_bytes

storage_safety = StorageSafetyManager()
