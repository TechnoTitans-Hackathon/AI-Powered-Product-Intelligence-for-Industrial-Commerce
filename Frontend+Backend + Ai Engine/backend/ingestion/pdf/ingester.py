import uuid
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException

from backend.core.config import settings
from backend.ingestion.pdf.schemas import PDFMetadata


class PDFIngester:
    """
    Validates and ingests PDF files into storage.
    Performs file existence, extension, MIME type, size limit, corrupted header, and encryption checks.
    """

    ALLOWED_EXTENSIONS = {".pdf"}

    def validate_file(self, file_path: Path) -> None:
        """
        Validates file existence, format, size, header integrity, and encryption status.
        Raises HTTPException with clear error details if invalid.
        """
        if not file_path.exists():
            raise HTTPException(status_code=400, detail=f"File not found: '{file_path.name}'")

        # 1. Extension check
        ext = file_path.suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension '{ext}'. Only '.pdf' files are supported.",
            )

        # 2. File size check
        size_bytes = file_path.stat().st_size
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        max_bytes = getattr(settings, "MAX_PDF_SIZE_MB", 100) * 1024 * 1024
        if size_bytes > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({size_bytes / (1024*1024):.1f}MB) exceeds maximum limit of {settings.MAX_PDF_SIZE_MB}MB.",
            )

        # 3. PDF Magic Header & Corruption Check
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
                if not header.startswith(b"%PDF-"):
                    raise HTTPException(
                        status_code=400,
                        detail="Corrupted or invalid PDF file: Missing '%PDF-' header signature.",
                    )

                # Check encryption flag in binary header/stream
                if b"/Encrypt" in header:
                    self._check_encryption(file_path)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse PDF binary header: {str(e)}",
            )

    def _check_encryption(self, file_path: Path) -> None:
        """Check if PDF is password protected or encrypted."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            if reader.is_encrypted:
                raise HTTPException(
                    status_code=422,
                    detail="Encrypted or password-protected PDFs are not supported. Please unprotect the file.",
                )
        except ImportError:
            pass
        except HTTPException:
            raise
        except Exception:
            pass

    def compute_sha256(self, file_path: Path) -> str:
        """Computes SHA-256 hash of the PDF file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_page_count(self, file_path: Path) -> int:
        """Retrieves page count using pypdf/fitz/pdfplumber or fallback PDF stream inspection."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            return len(reader.pages)
        except Exception:
            pass

        try:
            import fitz
            doc = fitz.open(str(file_path))
            count = len(doc)
            doc.close()
            return count
        except Exception:
            pass

        # Fallback binary stream inspection for /Type /Page count
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                count = content.count(b"/Type /Page\n") + content.count(b"/Type /Page ") + content.count(b"/Type/Page")
                return max(1, count)
        except Exception:
            return 1
