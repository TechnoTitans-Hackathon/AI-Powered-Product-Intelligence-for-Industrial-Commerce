import os
import shutil
from typing import Optional, Dict, Any
from backend.core.config import settings
from backend.core.logging import logger

class StorageManager:
    """
    Manages filesystem/object-storage abstractions for:
    1. Permanent Baseline Knowledge
    2. Temporary Knowledge Cache
    3. User Uploaded Source Files
    """

    def __init__(self):
        self.perm_dir = settings.PERMANENT_KNOWLEDGE_PATH
        self.temp_dir = settings.TEMP_CACHE_PATH
        self.user_dir = settings.USER_UPLOADS_PATH

    def store_user_upload(self, file_bytes: bytes, filename: str) -> str:
        os.makedirs(self.user_dir, exist_ok=True)
        filepath = os.path.join(self.user_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Stored user upload: {filepath} ({len(file_bytes)} bytes)")
        return filepath

    def store_temporary_knowledge(self, file_bytes: bytes, filename: str) -> str:
        os.makedirs(self.temp_dir, exist_ok=True)
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Stored temporary knowledge file: {filepath} ({len(file_bytes)} bytes)")
        return filepath

    def store_permanent_knowledge(self, file_bytes: bytes, filename: str) -> str:
        os.makedirs(self.perm_dir, exist_ok=True)
        filepath = os.path.join(self.perm_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Stored permanent baseline knowledge: {filepath} ({len(file_bytes)} bytes)")
        return filepath

    def get_file_path(self, storage_type: str, filename: str) -> Optional[str]:
        base_path = self.user_dir if storage_type == "user" else (self.temp_dir if storage_type == "temp" else self.perm_dir)
        filepath = os.path.join(base_path, filename)
        return filepath if os.path.exists(filepath) else None

storage_manager = StorageManager()
