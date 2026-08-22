import uuid
from typing import List
from backend.video_processing.schemas import (
    TimelineEvent,
    VisionObservation,
    OCRResult,
    TranscriptSegment,
    SelectedFrame,
    EvidenceRecord,
)


class TemporalAnalysisService:
    """
    Constructs chronological timeline events and fuses multimodal signals across video timestamps.
    Preserves event ordering, visual transitions, speech intervals, and OCR appearances.
    """

    def build_timeline(
        self,
        frames: List[SelectedFrame],
        observations: List[VisionObservation],
        ocr_results: List[OCRResult],
        transcripts: List[TranscriptSegment],
        evidence_list: List[EvidenceRecord],
    ) -> List[TimelineEvent]:
        timeline_events: List[TimelineEvent] = []

        # Helper map: find evidence IDs for a timestamp range or frame
        def get_evidence_ids_in_range(start_t: float, end_t: float) -> List[str]:
            matching = []
            for ev in evidence_list:
                ev_start = ev.timestamp_start if ev.timestamp_start is not None else 0.0
                ev_end = ev.timestamp_end if ev.timestamp_end is not None else ev_start
                if not (ev_end < start_t or ev_start > end_t):
                    matching.append(ev.evidence_id)
            return matching

        # 1. Timeline events from Scene/Visual Changes
        scene_frames = [f for f in frames if f.reason_selected in ("scene_change", "initial_frame")]
        for sf in scene_frames:
            ev_ids = [ev.evidence_id for ev in evidence_list if ev.frame_id == sf.frame_id]
            # Find matching visual observation
            obs_texts = [
                obs.value for obs in observations if obs.frame_id == sf.frame_id
            ]
            desc = obs_texts[0] if obs_texts else f"Scene transition at {sf.timestamp:.1f}s"
            
            timeline_events.append(
                TimelineEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    start=sf.timestamp,
                    end=round(sf.timestamp + 2.0, 2),
                    event=f"Scene/Visual Event: {desc}",
                    category="visual_scene",
                    evidence_ids=ev_ids,
                )
            )

        # 2. Timeline events from OCR Text Appearances
        for ocr in ocr_results:
            ev_ids = [ev.evidence_id for ev in evidence_list if ev.content == f"Visible Text: {ocr.text}"]
            timeline_events.append(
                TimelineEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    start=ocr.timestamp,
                    end=round(ocr.timestamp + 3.0, 2),
                    event=f"Text Appears on Screen: '{ocr.text}'",
                    category="ocr_text",
                    evidence_ids=ev_ids,
                )
            )

        # 3. Timeline events from Speech Segments
        for seg in transcripts:
            ev_ids = [ev.evidence_id for ev in evidence_list if ev.content == f"Spoken: {seg.text}"]
            timeline_events.append(
                TimelineEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    start=seg.start,
                    end=seg.end,
                    event=f"Spoken Statement: '{seg.text}'",
                    category="speech",
                    evidence_ids=ev_ids,
                )
            )

        # Sort timeline events chronologically by start timestamp
        timeline_events.sort(key=lambda x: x.start)

        # Merge closely adjacent or duplicate timeline events if necessary
        return self._deduplicate_timeline(timeline_events)

    def _deduplicate_timeline(self, events: List[TimelineEvent]) -> List[TimelineEvent]:
        if not events:
            return []

        merged: List[TimelineEvent] = []
        for evt in events:
            if not merged:
                merged.append(evt)
                continue

            last = merged[-1]
            # Merge identical events starting at exact same time
            if abs(last.start - evt.start) < 0.1 and last.event == evt.event:
                combined_ev_ids = list(set(last.evidence_ids + evt.evidence_ids))
                merged[-1] = TimelineEvent(
                    event_id=last.event_id,
                    start=last.start,
                    end=max(last.end, evt.end),
                    event=last.event,
                    category=last.category,
                    evidence_ids=combined_ev_ids,
                )
            else:
                merged.append(evt)

        return merged
