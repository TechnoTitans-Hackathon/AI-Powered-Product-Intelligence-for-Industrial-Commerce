import os
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
import cv2
import imageio_ffmpeg

from backend.core.config import settings
from backend.video_processing.schemas import VideoMetadata


class VideoDecoderError(Exception):
    """Exception raised during decoding operations."""
    pass


class VideoDecoderService:
    """
    Decodes video files to extract raw audio streams and specific timestamped frame images.
    """

    def __init__(self, frames_dir: Path = None, audio_dir: Path = None):
        if frames_dir is None:
            frames_dir = Path(settings.TEMP_CACHE_PATH) / "frames"
        if audio_dir is None:
            audio_dir = Path(settings.TEMP_CACHE_PATH) / "audio"
        self.frames_dir = Path(frames_dir)
        self.audio_dir = Path(audio_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def extract_audio(self, video_path: Path, video_id: str) -> Optional[Path]:
        """
        Extracts 16kHz mono WAV audio from the video file using FFmpeg.
        Returns path to extracted audio file, or None if no audio or extraction failed.
        """
        audio_filename = f"{video_id}.wav"
        output_audio_path = self.audio_dir / audio_filename

        if output_audio_path.exists():
            return output_audio_path

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",  # Overwrite output
            "-i", str(video_path),
            "-vn",  # Disable video
            "-acodec", "pcm_s16le",  # WAV encoding
            "-ar", "16000",  # 16kHz sampling rate for Speech-to-Text
            "-ac", "1",  # Mono
            str(output_audio_path)
        ]

        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
            )
            if result.returncode == 0 and output_audio_path.exists() and output_audio_path.stat().st_size > 0:
                return output_audio_path
            else:
                # Audio extraction produced no output or failed (e.g. video has no audio track)
                if output_audio_path.exists():
                    os.remove(output_audio_path)
                return None
        except Exception:
            if output_audio_path.exists():
                os.remove(output_audio_path)
            return None

    def extract_frame_at_timestamp(
        self, video_path: Path, video_id: str, timestamp_sec: float, frame_idx: int
    ) -> Optional[Tuple[Path, int]]:
        """
        Extracts a single frame at a specific timestamp (in seconds) and saves it as JPEG.
        Returns (frame_file_path, actual_frame_index) or None.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        target_frame = int(timestamp_sec * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        
        if not ret:
            # Fallback seek
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
            ret, frame = cap.read()

        cap.release()

        if not ret or frame is None:
            return None

        frame_filename = f"{video_id}_frame_{frame_idx:04d}_t{timestamp_sec:.2f}s.jpg"
        frame_file_path = self.frames_dir / frame_filename

        if not frame_file_path.exists():
            cv2.imwrite(str(frame_file_path), frame)

        return frame_file_path, target_frame
