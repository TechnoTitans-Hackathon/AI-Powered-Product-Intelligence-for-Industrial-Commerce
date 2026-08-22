import os
from backend.core.storage_safety import StorageSafetyManager
from backend.knowledge.cache_manager import cache_manager

def test_cache_and_4gb_storage_protection(tmp_path, db_session, monkeypatch):
    from backend.core.config import settings
    perm_dir = tmp_path / "perm_cache"
    perm_dir.mkdir()
    temp_dir = tmp_path / "temp_cache"
    temp_dir.mkdir()
    
    from backend.core.storage_safety import storage_safety
    monkeypatch.setattr(storage_safety, "max_temp_bytes", 1000)
    monkeypatch.setattr(storage_safety, "temp_cache_dir", str(temp_dir))
    monkeypatch.setattr(settings, "PERMANENT_KNOWLEDGE_PATH", str(perm_dir))
    
    safety = storage_safety

    # Create dummy temp file (600 bytes) via cache_manager so it is tracked in DB
    sample_content = b"A" * 600
    cache_manager.register_cache_item(
        db=db_session,
        source_id="src_test_evict",
        file_name="temp1.bin",
        file_bytes=sample_content,
        file_type="binary",
    )
    # The register_cache_item calls check_and_evict_cache. Since 600 < 1000, it succeeds.
    # Write the actual file where cache_manager expects it (temp_cache_dir)
    # Actually register_cache_item doesn't write the file, so let's mock the write
    file1 = temp_dir / "temp1.bin"
    file1.write_bytes(sample_content)

    stats = safety.get_storage_stats()
    assert stats["temporary_limit_bytes"] == 1000

    # Request 500 bytes (total 600 + 500 = 1100 > 1000 limit) -> triggers LRU eviction
    success = safety.check_and_evict_cache(db_session, required_bytes=500)
    assert success is True
    # file1 should have been evicted to make room
    assert not os.path.exists(str(file1))

def test_cache_registration_and_provenance(db_session):
    sample_content = b"Authoritative Datasheet Data"
    entry = cache_manager.register_cache_item(
        db=db_session,
        source_id="src_cache_01",
        file_name="datasheet.bin",
        file_bytes=sample_content,
        file_type="binary",
        url="https://example.com/datasheet.bin",
        provenance_metadata={"acquired_by": "unit_test"}
    )

    assert entry.source_id == "src_cache_01"
    assert entry.file_size_bytes == len(sample_content)
    assert entry.indexed_status is True
