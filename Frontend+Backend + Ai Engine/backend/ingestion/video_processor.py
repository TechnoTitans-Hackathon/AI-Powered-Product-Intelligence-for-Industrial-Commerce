import os
import asyncio
from typing import Dict, Any, Optional
from backend.ingestion.processor import SourceProcessor
from backend.schemas.source import ProcessedSource
from backend.ingestion.video.service import VideoIntelligenceService
from backend.ingestion.video.schemas import VideoAnalysisRequest
from backend.schemas.ai_contract import AIProcessingMode

class VideoProcessor(SourceProcessor):
    """
    Processes video source files using the VideoIntelligenceService.
    """

    def process(self, file_path: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedSource:
        meta = metadata or {}
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Use the configured global AI Processing Mode or default to AUTO
        ai_mode_str = os.environ.get("AI_PROCESSING_MODE", "AUTO").upper()
        try:
            ai_mode = AIProcessingMode[ai_mode_str]
        except KeyError:
            ai_mode = AIProcessingMode.AUTO

        service = VideoIntelligenceService(ai_mode=ai_mode)
        request = VideoAnalysisRequest(video_path=file_path)

        try:
            # VideoIntelligenceService.analyze_video is now async
            import threading
            
            result = []
            exc = []
            
            def run_in_thread():
                try:
                    res = asyncio.run(service.analyze_video(request))
                    result.append(res)
                except Exception as e:
                    exc.append(e)
            
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
            
            if exc:
                raise exc[0]
            response = result[0]
            
            # Format extracted text from timeline and evidence
            extracted_text_lines = [f"Video Recording: {filename}"]
            if response.timeline:
                for event in response.timeline:
                    extracted_text_lines.append(f"[{event.start}s - {event.end}s] {event.category.upper() if event.category else 'GENERAL'}: {event.event}")
            
            if response.evidence:
                extracted_text_lines.append("\nEvidence/Observations:")
                for ev in response.evidence:
                    extracted_text_lines.append(f"- {ev.type.value.upper()} ({ev.timestamp_start}s): {ev.content} (Confidence: {ev.confidence})")

            extracted_text = "\n".join(extracted_text_lines)

            return ProcessedSource(
                source_id=source_id,
                original_file=filename,
                source_type="video",
                extracted_text=extracted_text,
                metadata={
                    **meta,
                    "file_size": file_size,
                    "extraction_status": "success",
                    "analysis_id": response.analysis_id,
                    "video_id": response.video_id,
                    "processing_stats": response.processing.model_dump() if response.processing else {}
                },
                pages=1,
                tables=[],
                images=[],
                timestamps=[{"timestamp": ev.timestamp_start} for ev in response.evidence if ev.timestamp_start is not None] if response.evidence else []
            )

        except Exception as e:
            extracted_text = (
                f"[extraction_error] Video Recording: {filename}\n"
                f"Reason: {str(e)}\n"
                f"File size: {file_size} bytes\n"
            )
            return ProcessedSource(
                source_id=source_id,
                original_file=filename,
                source_type="video",
                extracted_text=extracted_text,
                metadata={
                    **meta,
                    "file_size": file_size,
                    "extraction_status": "error",
                    "extraction_reason": str(e)
                },
                pages=1,
                tables=[],
                images=[],
                timestamps=[]
            )
