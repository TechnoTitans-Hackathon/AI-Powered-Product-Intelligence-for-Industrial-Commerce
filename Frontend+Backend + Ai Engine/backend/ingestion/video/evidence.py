import uuid
from typing import List
from backend.ingestion.video.schemas import (
    EvidenceRecord,
    EvidenceType,
    VisionObservation,
    OCRResult,
    TranscriptSegment,
    VideoMetadata,
    SelectedFrame,
)


class MultimodalEvidenceBuilder:
    """
    Transforms raw visual observations, OCR text, and speech transcripts into
    canonical, traceable EvidenceRecord objects with strict timestamp and frame links.
    """

    def build_evidence(
        self,
        metadata: VideoMetadata,
        frames: List[SelectedFrame],
        observations: List[VisionObservation],
        ocr_results: List[OCRResult],
        transcripts: List[TranscriptSegment],
    ) -> List[EvidenceRecord]:
        evidence_list: List[EvidenceRecord] = []

        # 1. Metadata Evidence
        evidence_list.append(
            EvidenceRecord(
                evidence_id=f"ev_meta_{uuid.uuid4().hex[:8]}",
                type=EvidenceType.METADATA,
                timestamp_start=0.0,
                timestamp_end=metadata.duration_seconds,
                content=f"Video metadata: filename={metadata.filename}, duration={metadata.duration_seconds}s, resolution={metadata.width}x{metadata.height}, fps={metadata.fps}, has_audio={metadata.has_audio}",
                confidence=1.0,
                source="ingestion",
                metadata=metadata.model_dump(),
            )
        )

        # 2. Keyframe Scene Selection Evidence
        for frame in frames:
            evidence_list.append(
                EvidenceRecord(
                    evidence_id=f"ev_frame_{uuid.uuid4().hex[:8]}",
                    type=EvidenceType.SCENE,
                    timestamp_start=frame.timestamp,
                    timestamp_end=frame.timestamp,
                    frame_id=frame.frame_id,
                    content=f"Keyframe selected at {frame.timestamp:.2f}s due to '{frame.reason_selected}'",
                    confidence=1.0,
                    source="frame_selector",
                    metadata={"file_reference": frame.file_reference, "reason": frame.reason_selected},
                )
            )

        # 3. Visual Observations Evidence
        for obs in observations:
            ev_type = EvidenceType.VISUAL
            if obs.observation_type == "action":
                ev_type = EvidenceType.ACTION
            elif obs.observation_type == "scene":
                ev_type = EvidenceType.SCENE

            evidence_list.append(
                EvidenceRecord(
                    evidence_id=f"ev_vis_{uuid.uuid4().hex[:8]}",
                    type=ev_type,
                    timestamp_start=obs.timestamp,
                    timestamp_end=obs.timestamp,
                    frame_id=obs.frame_id,
                    content=f"Visual Observation ({obs.observation_type}): {obs.value}",
                    confidence=obs.confidence,
                    source="vision_analysis",
                    metadata={"bbox": obs.bbox, "details": obs.details},
                )
            )

        # 4. OCR Results Evidence
        for ocr in ocr_results:
            evidence_list.append(
                EvidenceRecord(
                    evidence_id=f"ev_ocr_{uuid.uuid4().hex[:8]}",
                    type=EvidenceType.OCR,
                    timestamp_start=ocr.timestamp,
                    timestamp_end=ocr.timestamp,
                    frame_id=ocr.frame_id,
                    content=f"Visible Text: {ocr.text}",
                    confidence=ocr.confidence,
                    source="ocr_analysis",
                    metadata={"ocr_id": ocr.ocr_id, "bbox": ocr.bbox},
                )
            )

        # 5. Speech Transcript Evidence
        for seg in transcripts:
            evidence_list.append(
                EvidenceRecord(
                    evidence_id=f"ev_stt_{uuid.uuid4().hex[:8]}",
                    type=EvidenceType.SPEECH,
                    timestamp_start=seg.start,
                    timestamp_end=seg.end,
                    content=f"Spoken: {seg.text}",
                    confidence=seg.confidence,
                    source="speech_analysis",
                    metadata={"segment_id": seg.segment_id, "speaker": seg.speaker},
                )
            )

        return evidence_list
