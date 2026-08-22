from typing import List, Optional
from backend.video_processing.schemas import (
    EvidenceRecord,
    EvidenceType,
    ConfidenceBreakdown,
    VideoMetadata,
)


class ConfidenceService:
    """
    Computes an empirical, multi-signal confidence metric for video analysis outputs.
    Combines individual modality confidence scores, evidence coverage, and temporal consistency.
    """

    def calculate_confidence(
        self,
        metadata: VideoMetadata,
        evidence_list: List[EvidenceRecord],
    ) -> ConfidenceBreakdown:
        if not evidence_list:
            return ConfidenceBreakdown(
                overall_confidence=0.0,
                ocr_confidence=None,
                stt_confidence=None,
                vision_confidence=None,
                evidence_coverage=0.0,
                temporal_consistency=0.0,
            )

        ocr_evs = [e for e in evidence_list if e.type == EvidenceType.OCR]
        stt_evs = [e for e in evidence_list if e.type == EvidenceType.SPEECH]
        vis_evs = [e for e in evidence_list if e.type in (EvidenceType.VISUAL, EvidenceType.SCENE, EvidenceType.ACTION)]

        ocr_conf = self._avg_confidence(ocr_evs)
        stt_conf = self._avg_confidence(stt_evs)
        vis_conf = self._avg_confidence(vis_evs)

        # 1. Evidence coverage (ratio of video duration covered by evidence timestamps)
        covered_seconds = 0.0
        dur = max(1.0, metadata.duration_seconds)
        time_points = set()

        for ev in evidence_list:
            if ev.timestamp_start is not None:
                time_points.add(round(ev.timestamp_start, 1))

        evidence_coverage = min(1.0, len(time_points) / max(1.0, dur / 2.0))

        # 2. Temporal consistency (degree of chronological alignment across evidence timestamps)
        timestamps = [e.timestamp_start for e in evidence_list if e.timestamp_start is not None]
        if len(timestamps) >= 2:
            is_sorted = all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))
            temporal_consistency = 0.95 if is_sorted else 0.80
        else:
            temporal_consistency = 0.90

        # Weighted aggregate overall confidence
        weights = []
        conf_values = []

        if vis_conf is not None:
            weights.append(0.35)
            conf_values.append(vis_conf)
        if stt_conf is not None:
            weights.append(0.35)
            conf_values.append(stt_conf)
        if ocr_conf is not None:
            weights.append(0.20)
            conf_values.append(ocr_conf)

        weights.append(0.10)
        conf_values.append(evidence_coverage)

        total_w = sum(weights)
        overall = sum(w * c for w, c in zip(weights, conf_values)) / total_w if total_w > 0 else 0.50

        return ConfidenceBreakdown(
            overall_confidence=round(overall, 2),
            ocr_confidence=round(ocr_conf, 2) if ocr_conf is not None else None,
            stt_confidence=round(stt_conf, 2) if stt_conf is not None else None,
            vision_confidence=round(vis_conf, 2) if vis_conf is not None else None,
            evidence_coverage=round(evidence_coverage, 2),
            temporal_consistency=round(temporal_consistency, 2),
        )

    def _avg_confidence(self, items: List[EvidenceRecord]) -> Optional[float]:
        if not items:
            return None
        return sum(item.confidence for item in items) / len(items)
