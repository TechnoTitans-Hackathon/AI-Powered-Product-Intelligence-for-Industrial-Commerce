from typing import Dict, Any, List, Optional
from backend.ingestion.video.schemas import VideoAnalysisResponse, EvidenceRecord, VideoMetadata


class MainAIIntegrationContract:
    """
    Exposes a standardized interface/contract for external platforms and main AI services.
    Ensures that domain-specific AI platforms can ingest video evidence and structured findings
    without introducing product-specific hardcoding inside the Video Intelligence Module.
    """

    def extract_canonical_evidence(
        self, analysis_response: VideoAnalysisResponse
    ) -> List[Dict[str, Any]]:
        """
        Converts the video analysis response into canonical evidence dictionaries
        suitable for platform vector DBs, RAG pipelines, or external product reasoners.
        """
        canonical_items = []
        for ev in analysis_response.evidence:
            canonical_items.append(
                {
                    "evidence_id": ev.evidence_id,
                    "video_id": analysis_response.video_id,
                    "modality_type": ev.type.value,
                    "timestamp_start": ev.timestamp_start,
                    "timestamp_end": ev.timestamp_end,
                    "frame_id": ev.frame_id,
                    "content": ev.content,
                    "confidence": ev.confidence,
                    "source": ev.source,
                    "provenance": {
                        "filename": analysis_response.metadata.filename,
                        "duration_seconds": analysis_response.metadata.duration_seconds,
                    },
                    "metadata": ev.metadata,
                }
            )
        return canonical_items

    def format_for_main_ai_rag(self, analysis_response: VideoAnalysisResponse) -> Dict[str, Any]:
        """
        Formats analysis output as a structured context package for the main platform LLM.
        """
        return {
            "video_metadata": analysis_response.metadata.model_dump(),
            "video_summary": analysis_response.summary,
            "timeline_events": [t.model_dump() for t in analysis_response.timeline],
            "verified_facts": [f.model_dump() for f in analysis_response.facts],
            "confidence_breakdown": analysis_response.confidence.model_dump(),
            "canonical_evidence": self.extract_canonical_evidence(analysis_response),
        }
