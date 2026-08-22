import os
import asyncio
from typing import Dict, Any, Optional
from backend.ingestion.processor import SourceProcessor
from backend.schemas.source import ProcessedSource
from backend.ingestion.image.orchestrator import analyze_image
from backend.core.logging import logger

class ImageProcessor(SourceProcessor):
    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        meta = metadata or {}
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(file_path)

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            import threading
            result = []
            exc = []
            
            def run_in_thread():
                try:
                    res = asyncio.run(analyze_image(image_bytes=image_bytes, filename=filename))
                    result.append(res)
                except Exception as e:
                    exc.append(e)
            
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
            
            if exc:
                raise exc[0]
            
            response = result[0]
            
            if not response.success:
                raise Exception(response.error.message if response.error else "Unknown image processing error")
                
            extracted_text_lines = [f"Image Document: {filename}"]
            
            if response.evidence:
                ev = response.evidence
                if getattr(ev, 'raw_text', None):
                    extracted_text_lines.append("\n--- OCR Text ---")
                    extracted_text_lines.append(ev.raw_text)
                if ev.visual_observations:
                    extracted_text_lines.append("\n--- Visual Observations ---")
                    for obs in ev.visual_observations:
                        extracted_text_lines.append(f"- {obs.observation} (Conf: {obs.confidence:.2f})")
            
            if response.product_intelligence:
                pi = response.product_intelligence
                extracted_text_lines.append("\n--- Product Intelligence ---")
                if pi.product_name and pi.product_name.value:
                    extracted_text_lines.append(f"Product Name: {pi.product_name.value}")
                if pi.model and pi.model.value:
                    extracted_text_lines.append(f"Model: {pi.model.value}")
                if pi.brand and pi.brand.value:
                    extracted_text_lines.append(f"Brand: {pi.brand.value}")
                if pi.description and pi.description.value:
                    extracted_text_lines.append(f"Description: {pi.description.value}")
            
            extracted_text = "\n".join(extracted_text_lines)
            
            return ProcessedSource(
                source_id=source_id,
                original_file=filename,
                source_type=f"image/{ext.replace('.', '')}",
                extracted_text=extracted_text,
                metadata={
                    **meta,
                    "file_size": file_size,
                    "format": ext,
                    "extraction_status": "success"
                },
                pages=1,
                tables=[],
                images=[{"filename": filename, "format": ext}],
                timestamps=[]
            )

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            extracted_text = (
                f"[extraction_error] Image Document: {filename}\n"
                f"Reason: {str(e)}\n"
                f"File size: {file_size} bytes\n"
            )
            return ProcessedSource(
                source_id=source_id,
                original_file=filename,
                source_type=f"image/{ext.replace('.', '')}",
                extracted_text=extracted_text,
                metadata={
                    **meta,
                    "file_size": file_size,
                    "format": ext,
                    "extraction_status": "error",
                    "extraction_reason": str(e)
                },
                pages=1,
                tables=[],
                images=[{"filename": filename, "format": ext}],
                timestamps=[]
            )
