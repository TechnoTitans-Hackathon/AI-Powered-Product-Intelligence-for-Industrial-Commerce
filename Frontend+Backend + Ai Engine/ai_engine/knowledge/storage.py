"""Temporary Knowledge System in-memory storage.

Provides in-memory implementation for the adaptive knowledge architecture.
Enforces:
- 4GB maximum limit
- 7-day retention after `last_used_at`
- Duplicate detection (URL/hash)
- LRU eviction
"""

import time
import hashlib
import uuid
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 7 days in seconds
SEVEN_DAYS = 7 * 24 * 60 * 60
# 4GB in bytes
FOUR_GB = 4 * 1024 * 1024 * 1024


@dataclass
class KnowledgeSource:
    source_id: str
    url: Optional[str]
    content_hash: str
    content: Any
    size_bytes: int
    metadata: dict[str, Any]
    is_permanent: bool
    created_at: float
    last_used_at: float


class TemporaryKnowledgeStore:
    """In-memory storage enforcing temporary knowledge limits."""

    def __init__(self, max_size_bytes: int = FOUR_GB, max_age_seconds: int = SEVEN_DAYS):
        self.sources: dict[str, KnowledgeSource] = {}
        self.max_size_bytes = max_size_bytes
        self.max_age_seconds = max_age_seconds
        
        # In this implementation, we keep indices for quick deduplication
        self._url_index: dict[str, str] = {}
        self._hash_index: dict[str, str] = {}

    def _estimate_size(self, content: Any) -> int:
        """Naive size estimation for the store."""
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            return len(content)
        # Default fallback for complex objects
        return 1024 * 10  # 10KB fallback

    def current_size(self) -> int:
        """Calculate total size of temporary knowledge."""
        return sum(s.size_bytes for s in self.sources.values() if not s.is_permanent)

    def prune_expired(self, current_time: Optional[float] = None) -> int:
        """Remove sources that haven't been used in 7 days."""
        now = current_time or time.time()
        expired_ids = [
            s_id for s_id, s in self.sources.items()
            if not s.is_permanent and (now - s.last_used_at) > self.max_age_seconds
        ]
        
        for s_id in expired_ids:
            self._remove(s_id)
            
        if expired_ids:
            logger.info(f"Pruned {len(expired_ids)} expired knowledge sources.")
            
        return len(expired_ids)

    def enforce_storage_limit(self) -> int:
        """Apply LRU eviction if temporary knowledge exceeds budget."""
        current = self.current_size()
        if current <= self.max_size_bytes:
            return 0
            
        logger.warning(f"Storage limit exceeded ({current} > {self.max_size_bytes}). Enforcing LRU eviction.")
        
        # Get all temporary sources, sorted by last_used_at ascending (oldest first)
        temp_sources = [s for s in self.sources.values() if not s.is_permanent]
        temp_sources.sort(key=lambda x: x.last_used_at)
        
        evicted_count = 0
        for s in temp_sources:
            if current <= self.max_size_bytes:
                break
            
            self._remove(s.source_id)
            current -= s.size_bytes
            evicted_count += 1
            
        logger.info(f"Evicted {evicted_count} sources to maintain 4GB limit.")
        return evicted_count

    def _remove(self, source_id: str):
        if source_id in self.sources:
            s = self.sources.pop(source_id)
            if s.url and s.url in self._url_index:
                del self._url_index[s.url]
            if s.content_hash in self._hash_index:
                del self._hash_index[s.content_hash]

    def add_temporary_source(self, content: Any, url: Optional[str] = None, metadata: Optional[dict] = None) -> str:
        """Add a temporary knowledge source, checking duplicates and limits."""
        self.prune_expired()
        
        # Duplicate detection
        if url and url in self._url_index:
            s_id = self._url_index[url]
            logger.debug(f"Source duplicate detected by URL: {url}")
            # Update last used
            self.sources[s_id].last_used_at = time.time()
            return s_id
            
        # Hash detection
        content_str = str(content).encode('utf-8')
        content_hash = hashlib.sha256(content_str).hexdigest()
        
        if content_hash in self._hash_index:
            s_id = self._hash_index[content_hash]
            logger.debug(f"Source duplicate detected by hash: {content_hash}")
            self.sources[s_id].last_used_at = time.time()
            return s_id
            
        # Calculate size and enforce limits
        size = self._estimate_size(content)
        
        # If this single item is too big, reject it (sanity check)
        if size > self.max_size_bytes:
            raise ValueError("Item exceeds maximum temporary storage capacity.")
            
        # Add new item
        s_id = str(uuid.uuid4())
        now = time.time()
        
        self.sources[s_id] = KnowledgeSource(
            source_id=s_id,
            url=url,
            content_hash=content_hash,
            content=content,
            size_bytes=size,
            metadata=metadata or {},
            is_permanent=False,
            created_at=now,
            last_used_at=now
        )
        
        if url:
            self._url_index[url] = s_id
        self._hash_index[content_hash] = s_id
        
        # Enforce limits *after* adding
        self.enforce_storage_limit()
        
        return s_id
        
    def add_permanent_source(self, source_id: str, content: Any, metadata: Optional[dict] = None):
        """Add baseline knowledge that is never evicted."""
        content_str = str(content).encode('utf-8')
        content_hash = hashlib.sha256(content_str).hexdigest()
        
        now = time.time()
        self.sources[source_id] = KnowledgeSource(
            source_id=source_id,
            url=None,
            content_hash=content_hash,
            content=content,
            size_bytes=self._estimate_size(content),
            metadata=metadata or {},
            is_permanent=True,
            created_at=now,
            last_used_at=now
        )
        
    def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Retrieve a source, updating its last_used_at timestamp."""
        if source_id not in self.sources:
            return None
            
        source = self.sources[source_id]
        if not source.is_permanent:
            source.last_used_at = time.time()
            
        return source
