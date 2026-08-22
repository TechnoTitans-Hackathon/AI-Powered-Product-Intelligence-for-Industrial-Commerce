from pathlib import Path
from typing import List
import cv2
import numpy as np

from backend.core.config import settings
from backend.ingestion.video.decoder import VideoDecoderService
from backend.ingestion.video.schemas import VideoMetadata, SelectedFrame


class IntelligentFrameSelector:
    """
    Implements a scene-aware and duration-adaptive frame selection strategy.
    Prioritizes key scenes, significant visual changes, and uniform sampling.
    Preserves exact timestamp for every selected frame.
    """

    def __init__(self, decoder: VideoDecoderService):
        self.decoder = decoder

    def select_keyframes(
        self, video_path: Path, metadata: VideoMetadata
    ) -> List[SelectedFrame]:
        """
        Extracts keyframes from the video using scene change detection and adaptive sampling.
        Returns a list of SelectedFrame metadata objects.
        """
        duration = metadata.duration_seconds
        fps = metadata.fps

        short_thresh = getattr(settings, 'SHORT_VIDEO_THRESHOLD_SEC', 15.0)
        long_thresh = getattr(settings, 'LONG_VIDEO_THRESHOLD_SEC', 60.0)
        
        # 1. Determine sampling interval based on video duration
        if duration <= short_thresh:
            target_fps = getattr(settings, 'SHORT_VIDEO_SAMPLING_FPS', 1.0)
        elif duration >= long_thresh:
            target_fps = getattr(settings, 'LONG_VIDEO_SAMPLING_FPS', 0.2)
        else:
            target_fps = getattr(settings, 'DEFAULT_SAMPLING_FPS', 0.5)

        step_seconds = max(0.5, 1.0 / target_fps)
        timestamps_to_check = []
        current_time = 0.0
        while current_time < duration:
            timestamps_to_check.append(round(current_time, 2))
            current_time += step_seconds

        # Ensure first and last frames are included if duration > 0
        if 0.0 not in timestamps_to_check:
            timestamps_to_check.insert(0, 0.0)
        last_t = round(max(0.0, duration - 0.5), 2)
        if last_t not in timestamps_to_check and last_t > 0:
            timestamps_to_check.append(last_t)

        selected_frames: List[SelectedFrame] = []

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return selected_frames

        prev_hist = None
        frame_counter = 0

        max_frames = getattr(settings, 'MAX_FRAMES_PER_ANALYSIS', 20)
        for t in timestamps_to_check:
            if len(selected_frames) >= max_frames:
                break

            target_frame_num = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # Calculate HSV histogram for scene change detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            reason = "periodic"
            if frame_counter == 0:
                reason = "initial_frame"
            elif prev_hist is not None:
                # Calculate correlation distance between frames
                score = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                scene_thresh = getattr(settings, 'SCENE_CHANGE_THRESHOLD', 0.3)
                if score < (1.0 - scene_thresh):
                    reason = "scene_change"

            prev_hist = hist
            frame_counter += 1

            # Save frame to disk via decoder
            res = self.decoder.extract_frame_at_timestamp(video_path, metadata.video_id, t, frame_counter)
            if res:
                frame_path, frame_idx = res
                frame_id = f"frame_{frame_counter:03d}"
                selected_frames.append(
                    SelectedFrame(
                        frame_id=frame_id,
                        timestamp=t,
                        frame_index=frame_idx,
                        file_reference=str(frame_path),
                        reason_selected=reason,
                    )
                )

        cap.release()
        return selected_frames
