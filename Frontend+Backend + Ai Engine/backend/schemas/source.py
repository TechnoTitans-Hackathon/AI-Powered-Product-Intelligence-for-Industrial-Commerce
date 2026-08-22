from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class SourceUploadResponse(BaseModel):
    source_id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    storage_path: str
    product_id: Optional[str] = None
    extracted_text_preview: Optional[str] = None
    pages: Optional[int] = None
    provenance: Dict[str, Any]

class ProcessedSource(BaseModel):
    source_id: str
    original_file: str
    source_type: str
    extracted_text: str
    metadata: Dict[str, Any]
    pages: Optional[int] = None
    tables: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    timestamps: List[Dict[str, Any]] = []
